"""Qualify frozen R19/R21E mesh stages against production R2A evidence requirements."""

# ruff: noqa: E501

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.immutable_pinned_evidence_admission import (
    verify_immutable_pinned_evidence,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.rating_pair_admission import (
    AdmittedLiveRating,
    admit_candidate_b_live_rating,
    admit_second_candidate_live_rating,
)
from prototypes.v07_fast_solver_live_rating_ladder_r13.stage_persistence import load_stage_receipt
from prototypes.v07_fast_solver_r2a_authority_qualification_r25.frozen_mesh_stage_pins import (
    ALL_FROZEN_MESH_PINS,
    R21E_N32_PROVIDER_AUTHORITY_ID,
    R21E_N64_PROVIDER_AUTHORITY_ID,
    FrozenMeshStagePin,
    receipt_path,
)
from prototypes.v07_fast_solver_r2a_authority_qualification_r25.r2a_certificate_verifier import (
    R2aCertificateEvidence,
    R2aVerificationOutcome,
    verify_r2a_certificate_evidence,
)
from prototypes.v07_fast_solver_r2a_producer_origin_r26.producer_non_trigger_witness import (
    evaluate_no_trigger_producer_witness,
)

R2A_ARTIFACT_KEYS = (
    "transient_provider_enclosure_event_hashes",
    "outer_decision_certificate_hashes",
    "outer_decision_certificate_projections",
    "outer_decision_action_sequence",
)


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_stage_bundle(root: Path, pin: FrozenMeshStagePin) -> dict[str, Any]:
    path = receipt_path(root, pin)
    if not path.is_file():
        raise FileNotFoundError(pin.receipt_rel)
    digest = _file_sha256(path)
    if pin.receipt_sha256 and digest != pin.receipt_sha256:
        raise ValueError(
            f"STAGE_RECEIPT_SHA256_MISMATCH mesh_n={pin.mesh_n} expected={pin.receipt_sha256}"
        )
    wrapper = json.loads(path.read_text(encoding="utf-8"))
    receipt = load_stage_receipt(path)
    return {"wrapper": wrapper, "receipt": receipt, "file_sha256": digest}


def _extract_r2a_artifacts(receipt: dict[str, Any], wrapper: dict[str, Any]) -> dict[str, Any]:
    found: dict[str, Any] = {}
    for key in R2A_ARTIFACT_KEYS:
        if key in receipt:
            found[key] = receipt[key]
        elif key in wrapper:
            found[key] = wrapper[key]
    return found


def _provider_from_trials_jsonl(root: Path, receipt: dict[str, Any]) -> tuple[str, str]:
    rel = receipt.get("trials_jsonl_rel_path")
    if not rel:
        return ("UNKNOWN", "UNKNOWN")
    path = root / str(rel)
    if not path.is_file():
        return ("MISSING_TRIALS_JSONL", "MISSING")
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
        authority = str(row.get("numerical_authority_id") or meta.get("authority_id") or "UNKNOWN")
        version = str(row.get("schema_version") or meta.get("schema_version") or "UNKNOWN")
        if authority != "UNKNOWN":
            return authority, version
    return ("UNKNOWN", "UNKNOWN")


def qualify_frozen_mesh_pin(
    root: Path,
    admitted: AdmittedLiveRating,
    pin: FrozenMeshStagePin,
) -> dict[str, Any]:
    imm = verify_immutable_pinned_evidence(root, admitted)
    if imm is not None:
        code, diag = imm
        return {
            "admission_status": "BLOCKED",
            "blocked_code": code,
            "diagnostics": list(diag),
            "pin": pin,
        }

    bundle = _load_stage_bundle(root, pin)
    receipt = bundle["receipt"]
    if receipt.get("candidate_id") != pin.candidate_id:
        return {
            "admission_status": "BLOCKED",
            "blocked_code": "STAGE_CANDIDATE_ID_MISMATCH",
            "pin": pin,
        }
    if receipt.get("rating_request_hash") != pin.rating_request_hash:
        return {
            "admission_status": "BLOCKED",
            "blocked_code": "STAGE_RATING_REQUEST_HASH_MISMATCH",
            "pin": pin,
        }
    if receipt.get("mesh_result_hash") != pin.expected_mesh_result_hash:
        return {
            "admission_status": "BLOCKED",
            "blocked_code": "STAGE_MESH_RESULT_HASH_MISMATCH",
            "pin": pin,
        }
    if receipt.get("worker_status") != "TERMINAL_ACCEPTED":
        return {
            "admission_status": "BLOCKED",
            "blocked_code": "STAGE_NOT_TERMINAL_ACCEPTED",
            "pin": pin,
        }

    r2a_artifacts = _extract_r2a_artifacts(receipt, bundle["wrapper"])
    has_r2a_hashes = any(
        bool(r2a_artifacts.get(key))
        for key in (
            "transient_provider_enclosure_event_hashes",
            "outer_decision_certificate_hashes",
        )
    )
    provider_id, provider_version = _provider_from_trials_jsonl(root, receipt)
    if provider_id == "UNKNOWN" and pin.label == "SECOND_CANDIDATE_R21E":
        provider_id = (
            R21E_N32_PROVIDER_AUTHORITY_ID if pin.mesh_n == 32 else R21E_N64_PROVIDER_AUTHORITY_ID
        )
        provider_version = "experimental-general-live"

    evidence = R2aCertificateEvidence(
        candidate_id=pin.candidate_id,
        candidate_hash=admitted.request.candidate_hash,
        rating_request_hash=pin.rating_request_hash,
        task174_result_hash=admitted.request.task174_result.result_hash,
        source_result_hash=admitted.full.result_hash,
        mesh_n=pin.mesh_n,
        mesh_identity=str(receipt.get("mesh_result_hash") or pin.expected_mesh_result_hash),
        mesh_result_hash=pin.expected_mesh_result_hash,
        provider_identity_id=provider_id,
        provider_identity_version=provider_version,
        transient_events=(),
        outer_certificates=(),
    )
    verifier: R2aVerificationOutcome = verify_r2a_certificate_evidence(evidence)

    non_trigger_status, non_trigger_detail = evaluate_no_trigger_producer_witness(None, root=root)

    if has_r2a_hashes:
        status = "CERTIFICATE_REQUIRED_BUT_MISSING"
        detail = "Stage references R2A hash fields but projections are not in frozen receipt."
    elif verifier.status == "PRODUCTION_CERTIFICATE_VERIFIED":
        status = verifier.status
        detail = ""
    elif verifier.status == "FROZEN_EVIDENCE_INSUFFICIENT":
        status = non_trigger_status
        detail = non_trigger_detail
        if verifier.diagnostics:
            detail = f"{detail}; {verifier.diagnostics[0]}"
    else:
        status = verifier.status
        detail = verifier.blocked_code or non_trigger_detail

    production_r2a_replay = (
        "CERTIFICATE_PRESENT_VERIFIED" if status == "PRODUCTION_CERTIFICATE_VERIFIED" else "BLOCKED"
    )

    return {
        "schema_version": "task173.r2a-frozen-mesh-qualification.v1",
        "label": pin.label,
        "candidate_id": pin.candidate_id,
        "mesh_n": pin.mesh_n,
        "mesh_role": pin.mesh_role,
        "mesh_result_hash": pin.expected_mesh_result_hash,
        "stage_receipt_rel": pin.receipt_rel,
        "stage_receipt_sha256": bundle["file_sha256"],
        "rating_request_hash": pin.rating_request_hash,
        "source_result_hash": admitted.full.result_hash,
        "provider_identity_id": provider_id,
        "provider_identity_version": provider_version,
        "r2a_artifacts_present": r2a_artifacts,
        "admission_status": status,
        "production_r2a_certificate_replay": production_r2a_replay,
        "detail": detail,
        "verifier_result_hash": verifier.result_hash,
    }


def qualify_all_frozen_candidates(root: Path) -> list[dict[str, Any]]:
    admitted_by_label = {
        "CANDIDATE_B_R19": admit_candidate_b_live_rating(root),
        "SECOND_CANDIDATE_R21E": admit_second_candidate_live_rating(root),
    }
    rows: list[dict[str, Any]] = []
    for pin in ALL_FROZEN_MESH_PINS:
        admitted = admitted_by_label[pin.label]
        rows.append(qualify_frozen_mesh_pin(root, admitted, pin))
    return rows
