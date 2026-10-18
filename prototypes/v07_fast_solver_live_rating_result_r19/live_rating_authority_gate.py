"""Fail-closed authority gates for LIVE_NUMERICAL_SOLVE rating entry."""

from __future__ import annotations

from pathlib import Path

from prototypes.v07_fast_solver_live_ladder_continuation_r14.comparison_history_admission import (
    comparison_canonical_sha256,
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


def _evidence_fingerprint(chain: LiveMeshEvidenceChain) -> tuple:
    cmp_hashes = tuple(comparison_canonical_sha256(c) for c in chain.mesh_comparisons)
    return (
        chain.rating_request_hash,
        chain.snapshot_rel_path,
        chain.ladder_status,
        chain.headroom_status,
        cmp_hashes,
        chain.evidence_chain_hashes,
    )


def enforce_live_rating_authority_gates(
    root: Path,
    evidence: LiveMeshEvidenceChain,
) -> tuple[LiveMeshEvidenceChain, ExperimentalRatingBlocked | None]:
    """Re-admit pinned evidence from disk; reject tampered caller-supplied chains."""
    try:
        refreshed = admit_full_live_mesh_evidence(
            root,
            candidate_id=evidence.request.candidate_id,
        )
    except LiveEvidenceAdmissionError as exc:
        return evidence, _blocked(exc.code, *exc.diagnostics)

    if _evidence_fingerprint(evidence) != _evidence_fingerprint(refreshed):
        return refreshed, _blocked("LIVE_EVIDENCE_CHAIN_TAMPER_DETECTED")

    chain_err = _validate_mesh_comparison_chain(refreshed.mesh_comparisons)
    if chain_err is not None:
        return refreshed, chain_err

    if refreshed.ladder_status != "HEADROOM_PASS" or refreshed.headroom_status != "PASS":
        return refreshed, _blocked(
            "LADDER_OR_HEADROOM_STATUS_INVALID",
            refreshed.ladder_status,
            refreshed.headroom_status,
        )

    if not verify_task174_binding(refreshed.request):
        return refreshed, _blocked("TASK174_BINDING_GATE_FAILED")

    if refreshed.request.candidate_id != evidence.request.candidate_id:
        return refreshed, _blocked("CANDIDATE_ID_MISMATCH")

    if refreshed.rating_request_hash != evidence.rating_request_hash:
        return refreshed, _blocked("RATING_REQUEST_HASH_MISMATCH")

    return refreshed, None
