"""Fail-closed authority gates for LIVE_NUMERICAL_SOLVE rating entry."""

from __future__ import annotations

import json
from pathlib import Path

from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
    CandidateRatingRequest,
    candidate_rating_request_hash,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.comparison_history_admission import (
    comparison_canonical_sha256,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.native_codec import native_projection
from prototypes.v07_fast_solver_live_ladder_continuation_r14.request_snapshot import (
    upstream_binding_hashes,
)
from prototypes.v07_fast_solver_live_rating_result_r19.live_evidence_admission import (
    LiveEvidenceAdmissionError,
    LiveMeshEvidenceChain,
    admit_full_live_mesh_evidence,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.experimental_models import (
    ExperimentalRatingBlocked,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.verification import (
    verify_task174_binding,
)

REQUIRED_CONSECUTIVE_PASSING_PAIRS = 2


def _blocked(code: str, *diag: str) -> ExperimentalRatingBlocked:
    return ExperimentalRatingBlocked(
        status="BLOCKED",
        blocked_code=code,
        blocked_diagnostics=diag,
        execution_mode="LIVE_NUMERICAL_SOLVE",
    )


def _validate_mesh_comparison_chain(
    comparisons: tuple[dict, ...],
) -> ExperimentalRatingBlocked | None:
    if len(comparisons) < 6:
        return _blocked("INCOMPLETE_MESH_COMPARISON_CHAIN", str(len(comparisons)))
    statuses = [str(c.get("overall_status")) for c in comparisons]
    if statuses != ["FAIL", "FAIL", "FAIL", "PASS", "PASS", "PASS"]:
        return _blocked("MESH_COMPARISON_STATUS_SEQUENCE_MISMATCH", ",".join(statuses))
    pass_runs = 0
    for status in statuses:
        if status == "PASS":
            pass_runs += 1
        else:
            pass_runs = 0
        if pass_runs >= REQUIRED_CONSECUTIVE_PASSING_PAIRS:
            break
    else:
        return _blocked("MESH_CANDIDATE_CONSECUTIVE_PASS_NOT_FOUND")
    last = comparisons[-1]
    if int(last.get("coarse_subdivisions", 0)) != 32 or int(last.get("fine_subdivisions", 0)) != 64:
        return _blocked("HEADROOM_COMPARISON_PAIR_MISMATCH")
    if last.get("overall_status") != "PASS":
        return _blocked("HEADROOM_COMPARISON_NOT_PASS")
    threshold = str(last.get("duty_metric_threshold", ""))
    if threshold != "0.01":
        return _blocked("DUTY_METRIC_THRESHOLD_MISMATCH", threshold)
    return None


def _stage_canonical(stage: dict) -> str:
    return json.dumps(stage, sort_keys=True, separators=(",", ":"))


def _mesh_stages_fingerprint(stages: tuple[dict, ...]) -> tuple[str, ...]:
    return tuple(_stage_canonical(s) for s in stages)


def _deep_request_structural_match(
    caller: CandidateRatingRequest,
    trusted: CandidateRatingRequest,
) -> ExperimentalRatingBlocked | None:
    caller_proj = native_projection(caller)
    trusted_proj = native_projection(trusted)
    if caller_proj != trusted_proj:
        return _blocked("CALLER_REQUEST_TAMPER_BLOCKED", "native_projection_deep_mismatch")
    try:
        caller_bindings = upstream_binding_hashes(caller)
        trusted_bindings = upstream_binding_hashes(trusted)
    except (TypeError, ValueError) as exc:
        return _blocked("CALLER_REQUEST_TAMPER_BLOCKED", f"upstream_binding_compute:{exc}")
    for key, trusted_value in trusted_bindings.items():
        if caller_bindings.get(key) != trusted_value:
            return _blocked(
                "CALLER_REQUEST_TAMPER_BLOCKED",
                "upstream_binding_mismatch",
                key,
            )
    return None


def _caller_vs_trusted_tamper_check(
    evidence: LiveMeshEvidenceChain,
    trusted: LiveMeshEvidenceChain,
) -> ExperimentalRatingBlocked | None:
    if evidence.snapshot_rel_path != trusted.snapshot_rel_path:
        return _blocked(
            "CALLER_REQUEST_TAMPER_BLOCKED",
            "snapshot_rel_path",
            evidence.snapshot_rel_path,
            trusted.snapshot_rel_path,
        )
    if evidence.rating_request_hash != trusted.rating_request_hash:
        return _blocked(
            "CALLER_REQUEST_TAMPER_BLOCKED",
            "rating_request_hash",
            evidence.rating_request_hash,
            trusted.rating_request_hash,
        )
    caller_req_hash = candidate_rating_request_hash(evidence.request)
    trusted_req_hash = candidate_rating_request_hash(trusted.request)
    if caller_req_hash != trusted_req_hash:
        return _blocked("CALLER_REQUEST_TAMPER_BLOCKED", "request_hash_replay")
    if evidence.request.candidate_id != trusted.request.candidate_id:
        return _blocked("CALLER_REQUEST_TAMPER_BLOCKED", "candidate_id")
    if evidence.request.candidate_hash != trusted.request.candidate_hash:
        return _blocked("CALLER_REQUEST_TAMPER_BLOCKED", "candidate_hash")

    deep = _deep_request_structural_match(evidence.request, trusted.request)
    if deep is not None:
        return deep

    if not verify_task174_binding(evidence.request):
        return _blocked("CALLER_TASK174_BINDING_TAMPER_BLOCKED", "caller_request")
    if evidence.request.task174_result.result_hash != trusted.request.task174_result.result_hash:
        return _blocked(
            "CALLER_TASK174_BINDING_TAMPER_BLOCKED",
            evidence.request.task174_result.result_hash,
            trusted.request.task174_result.result_hash,
        )

    if _mesh_stages_fingerprint(evidence.mesh_stages) != _mesh_stages_fingerprint(
        trusted.mesh_stages
    ):
        return _blocked("CALLER_MESH_STAGE_TAMPER_BLOCKED")

    if len(evidence.mesh_comparisons) != len(trusted.mesh_comparisons):
        return _blocked("CALLER_MESH_COMPARISON_TAMPER_BLOCKED", "count_mismatch")
    for index, (caller_cmp, trusted_cmp) in enumerate(
        zip(evidence.mesh_comparisons, trusted.mesh_comparisons, strict=True)
    ):
        if comparison_canonical_sha256(caller_cmp) != comparison_canonical_sha256(trusted_cmp):
            return _blocked("CALLER_MESH_COMPARISON_TAMPER_BLOCKED", f"index={index}")

    if evidence.ladder_status != trusted.ladder_status:
        return _blocked(
            "CALLER_HEADROOM_EVIDENCE_TAMPER_BLOCKED",
            "ladder_status",
            evidence.ladder_status,
            trusted.ladder_status,
        )
    if evidence.headroom_status != trusted.headroom_status:
        return _blocked(
            "CALLER_HEADROOM_EVIDENCE_TAMPER_BLOCKED",
            "headroom_status",
            evidence.headroom_status,
            trusted.headroom_status,
        )

    if evidence.evidence_chain_hashes != trusted.evidence_chain_hashes:
        return _blocked("CALLER_MESH_COMPARISON_TAMPER_BLOCKED", "evidence_chain_hashes")

    return None


def enforce_live_rating_authority_gates(
    root: Path,
    evidence: LiveMeshEvidenceChain,
) -> tuple[LiveMeshEvidenceChain, ExperimentalRatingBlocked | None]:
    """Re-admit pinned evidence from disk; reject caller tampering with explicit codes."""
    try:
        trusted = admit_full_live_mesh_evidence(
            root,
            candidate_id=evidence.request.candidate_id,
        )
    except LiveEvidenceAdmissionError as exc:
        return evidence, _blocked(exc.code, *exc.diagnostics)

    tamper = _caller_vs_trusted_tamper_check(evidence, trusted)
    if tamper is not None:
        return evidence, tamper

    chain_err = _validate_mesh_comparison_chain(trusted.mesh_comparisons)
    if chain_err is not None:
        return evidence, chain_err

    if trusted.ladder_status != "HEADROOM_PASS" or trusted.headroom_status != "PASS":
        return evidence, _blocked(
            "LADDER_OR_HEADROOM_STATUS_INVALID",
            trusted.ladder_status,
            trusted.headroom_status,
        )

    if not verify_task174_binding(trusted.request):
        return evidence, _blocked("TASK174_BINDING_GATE_FAILED")

    return evidence, None
