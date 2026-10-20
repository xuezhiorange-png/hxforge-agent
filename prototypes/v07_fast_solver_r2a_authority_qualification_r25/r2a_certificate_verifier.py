"""Verify production R2A transient events and outer decision certificates."""

# ruff: noqa: E501

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
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
    R2A_AUTHORITY_HASH,
    R2A_AUTHORITY_ID,
    R2A_CERTIFICATE_SCHEMA,
    R2A_EVENT_SCHEMA,
)
from prototypes.v07_fast_solver_r2a_producer_origin_r26.captured_producer_fixture import (
    _restore_candidate_json_values,
)
from prototypes.v07_fast_solver_r2a_producer_origin_r26.producer_origin_verification import (
    verify_producer_origin_record,
)
from prototypes.v07_fast_solver_r2a_producer_origin_r26.q_predicate_independent_replay import (
    APPROVED_PROVIDER,
    verify_event_q_independent_replay,
    verify_producer_provider_identity,
)

ROOT = Path(__file__).resolve().parents[2]

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
    producer_replay_arguments: dict[str, Any] | None = None
    producer_origin: dict[str, Any] | None = None


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


def _verify_producer_identity(evidence: R2aCertificateEvidence) -> tuple[bool, str]:
    if evidence.provider_identity_id != R2A_AUTHORITY_ID:
        return False, "R2A_PRODUCER_AUTHORITY_MISMATCH"
    if evidence.provider_identity_version != APPROVED_PROVIDER["provider_version"]:
        return False, "R2A_PROVIDER_VERSION_MISMATCH"
    if evidence.producer_origin is not None:
        ok, code = verify_producer_origin_record(evidence.producer_origin, root=ROOT)
        if not ok:
            return False, code
    return True, "PASS"


def _verify_endpoint_hashes(event: dict[str, Any]) -> tuple[bool, str]:
    for side in ("left", "right"):
        req_proj = event.get(f"endpoint_request_projection_{side}")
        res_proj = event.get(f"endpoint_result_projection_{side}")
        if not isinstance(req_proj, dict) or not isinstance(res_proj, dict):
            return False, "R2A_ENDPOINT_PROJECTION_MISSING"
        try:
            request = CandidateTask172LocalRequest.model_validate(
                _restore_candidate_json_values(req_proj), strict=False
            )
            result = Task172LocalResult.model_validate(res_proj, strict=False)
        except Exception:
            return False, "R2A_ENDPOINT_PROJECTION_INVALID"
        req_hash = recompute_task172_request_hash(request)
        res_hash = recompute_task172_result_hash(result)
        if req_hash != event.get(f"{side}_endpoint_request_hash"):
            return False, f"R2A_{side.upper()}_ENDPOINT_REQUEST_HASH_MISMATCH"
        if res_hash != event.get(f"{side}_endpoint_result_hash"):
            return False, f"R2A_{side.upper()}_ENDPOINT_RESULT_HASH_MISMATCH"
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
    ok, code = verify_producer_provider_identity(event)
    if not ok:
        return False, code
    if evidence.producer_replay_arguments is not None:
        pid = evidence.producer_replay_arguments.get("provider_identity") or {}
        if pid.get("provider") != APPROVED_PROVIDER["provider"]:
            return False, "R2A_PROVIDER_IDENTITY_MISMATCH"
        if pid.get("provider_version") != APPROVED_PROVIDER["provider_version"]:
            return False, "R2A_PROVIDER_VERSION_MISMATCH"
    ok, code = _verify_endpoint_hashes(event)
    if not ok:
        return False, code
    ok, code, _ = verify_event_q_independent_replay(
        event,
        producer_arguments=evidence.producer_replay_arguments,
    )
    if not ok:
        return False, code
    return True, "PASS"


def _verify_certificate(
    certificate: dict[str, Any],
    evidence: R2aCertificateEvidence,
    event_hashes: set[str],
    event_by_hash: dict[str, dict[str, Any]],
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
    if left_events:
        left_event = event_by_hash.get(left_events[0])
        if left_event is not None:
            if certificate.get("left_branch_used_endpoint_request_hash") != left_event.get(
                "left_endpoint_request_hash"
            ):
                return False, "R2A_CERTIFICATE_LEFT_BRANCH_REQUEST_MISMATCH"
            if certificate.get("left_branch_used_endpoint_result_hash") != left_event.get(
                "left_endpoint_result_hash"
            ):
                return False, "R2A_CERTIFICATE_LEFT_BRANCH_RESULT_MISMATCH"
    if right_events:
        right_event = event_by_hash.get(right_events[0])
        if right_event is not None:
            if certificate.get("right_branch_used_endpoint_request_hash") != right_event.get(
                "right_endpoint_request_hash"
            ):
                return False, "R2A_CERTIFICATE_RIGHT_BRANCH_REQUEST_MISMATCH"
            if certificate.get("right_branch_used_endpoint_result_hash") != right_event.get(
                "right_endpoint_result_hash"
            ):
                return False, "R2A_CERTIFICATE_RIGHT_BRANCH_RESULT_MISMATCH"
    trigger = certificate.get("trigger_support_id")
    if trigger is None:
        return False, "R2A_CERTIFICATE_TRIGGER_SUPPORT_MISSING"
    if certificate.get("midpoint_collapse_disposition_invariant") is not True:
        return False, "R2A_CERTIFICATE_MIDPOINT_INVARIANT_MISMATCH"
    for field in (
        "left_branch_used_endpoint_request_hash",
        "left_branch_used_endpoint_result_hash",
        "right_branch_used_endpoint_request_hash",
        "right_branch_used_endpoint_result_hash",
    ):
        if not certificate.get(field):
            return False, "R2A_CERTIFICATE_ENDPOINT_BINDING_MISSING"
    if certificate.get("shooting_enthalpy_j_kg") is None:
        return False, "R2A_CERTIFICATE_SHOOTING_ENTHALPY_MISSING"
    if certificate.get("outer_iteration") is None:
        return False, "R2A_CERTIFICATE_OUTER_ITERATION_MISSING"
    left_cont = certificate.get("left_continuation_hash")
    right_cont = certificate.get("right_continuation_hash")
    if not left_cont or not right_cont:
        return False, "R2A_CERTIFICATE_CONTINUATION_HASH_MISSING"
    if (
        certificate.get("left_outer_action") is None
        or certificate.get("right_outer_action") is None
    ):
        return False, "R2A_CERTIFICATE_OUTER_ACTION_MISSING"
    return True, "PASS"


def verify_r2a_certificate_evidence(evidence: R2aCertificateEvidence) -> R2aVerificationOutcome:
    if not evidence.candidate_id or not evidence.rating_request_hash:
        return _fail("R2A_BINDING_INCOMPLETE", "candidate_or_request_missing")
    has_events = bool(evidence.transient_events)
    has_certs = bool(evidence.outer_certificates)
    provider_ok = False
    if has_events or has_certs:
        provider_ok, provider_code = _verify_producer_identity(evidence)
        if not provider_ok:
            return _fail(provider_code)
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
    event_by_hash: dict[str, dict[str, Any]] = {}
    for event in evidence.transient_events:
        ok, code = _verify_event(event, evidence)
        if not ok:
            return _fail(code)
        event_hashes.add(str(event["event_hash"]))
        event_by_hash[str(event["event_hash"])] = event

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
        ok, code = _verify_certificate(certificate, evidence, event_hashes, event_by_hash)
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
