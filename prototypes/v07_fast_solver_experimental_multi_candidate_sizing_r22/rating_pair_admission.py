"""Admit pinned R19 Candidate B and R21E second-candidate live ratings."""

# ruff: noqa: E501

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
    CandidateRatingRequest,
    candidate_rating_request_hash,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.pinned_r21e_full_gate import (
    load_and_verify_pinned_r21e_full,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.r22_pinned_identity import (
    R21E_COMPACT_HASH,
    R21E_COMPACT_REL,
    R21E_FULL_JSON_REL,
)
from prototypes.v07_fast_solver_general_candidate_live_rating_r21 import (
    general_live_compact_rating as glcr,
)
from prototypes.v07_fast_solver_general_candidate_live_rating_r21.general_live_result_hash import (
    GENERAL_LIVE_RATING_R21_AUTHORITY_ID,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.request_snapshot import (
    load_request_from_snapshot_file,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.experimental_models import (
    ExperimentalCandidateRatingResult,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.geometry_summary import (
    geometry_summary_from_request,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.experimental_sizing_rating_adapter import (
    load_verified_live_compact_from_r19_audit,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.live_compact_rating import (
    LiveCompactCandidateRating,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.pinned_r19_full_gate import (
    load_and_verify_pinned_r19_full,
)


class RatingAdmissionError(RuntimeError):
    def __init__(self, code: str, *diagnostics: str) -> None:
        self.code = code
        self.diagnostics = diagnostics
        super().__init__(code)


@dataclass(frozen=True)
class AdmittedLiveRating:
    label: str
    full: ExperimentalCandidateRatingResult
    compact_r19: LiveCompactCandidateRating | None
    compact_general: glcr.GeneralLiveCompactCandidateRating | None
    request: CandidateRatingRequest
    full_audit: dict[str, Any]
    full_file_sha256: str
    snapshot_rel_path: str


def _load_r21e_compact(root: Path) -> glcr.GeneralLiveCompactCandidateRating:
    path = root / R21E_COMPACT_REL
    compact = glcr.GeneralLiveCompactCandidateRating.model_validate_json(
        path.read_text(encoding="utf-8"),
        strict=True,
    )
    if compact.compact_result_hash != glcr.general_live_compact_rating_hash(compact):
        raise RatingAdmissionError("R21E_COMPACT_HASH_REPLAY_MISMATCH")
    if compact.compact_result_hash != R21E_COMPACT_HASH:
        raise RatingAdmissionError("R21E_COMPACT_HASH_NOT_PINNED")
    if compact.experimental_rating_authority_id != GENERAL_LIVE_RATING_R21_AUTHORITY_ID:
        raise RatingAdmissionError("R21E_COMPACT_AUTHORITY_MISMATCH")
    return compact


def admit_candidate_b_live_rating(root: Path) -> AdmittedLiveRating:
    full, audit, full_sha = load_and_verify_pinned_r19_full(root)
    compact, _ = load_verified_live_compact_from_r19_audit(root)
    snapshot_rel = str(dict(full.provenance).get("snapshot_rel_path") or "")
    if not snapshot_rel:
        raise RatingAdmissionError("R19_MISSING_SNAPSHOT_PROVENANCE")
    request = load_request_from_snapshot_file(root / snapshot_rel)
    if candidate_rating_request_hash(request) != full.rating_request_hash:
        raise RatingAdmissionError("R19_SNAPSHOT_REQUEST_HASH_MISMATCH")
    geom = geometry_summary_from_request(request)
    from prototypes.v07_fast_solver_rating_sizing_bridge_r20.live_compact_rating import (
        verify_live_compact_against_full,
    )

    verify_live_compact_against_full(
        compact, full, full_file_sha256=full_sha, geometry_summary=geom
    )
    return AdmittedLiveRating(
        label="CANDIDATE_B_R19",
        full=full,
        compact_r19=compact,
        compact_general=None,
        request=request,
        full_audit=audit,
        full_file_sha256=full_sha,
        snapshot_rel_path=snapshot_rel,
    )


def admit_second_candidate_live_rating(root: Path) -> AdmittedLiveRating:
    full, audit, full_sha = load_and_verify_pinned_r21e_full(root)
    compact = _load_r21e_compact(root)
    if compact.full_trajectory_artifact.path != R21E_FULL_JSON_REL:
        raise RatingAdmissionError("R21E_COMPACT_FULL_PATH_MISMATCH")
    if compact.full_trajectory_artifact.file_sha256 != full_sha:
        raise RatingAdmissionError("R21E_COMPACT_FULL_SHA_MISMATCH")
    if compact.full_result_hash != full.result_hash:
        raise RatingAdmissionError("R21E_COMPACT_FULL_HASH_MISMATCH")
    snapshot_rel = str(dict(full.provenance).get("snapshot_rel_path") or "")
    if not snapshot_rel:
        raise RatingAdmissionError("R21E_MISSING_SNAPSHOT_PROVENANCE")
    request = load_request_from_snapshot_file(root / snapshot_rel)
    if candidate_rating_request_hash(request) != full.rating_request_hash:
        raise RatingAdmissionError("R21E_SNAPSHOT_REQUEST_HASH_MISMATCH")
    geom = geometry_summary_from_request(request)
    glcr.verify_general_live_compact_against_full(
        compact,
        full,
        full_file_sha256=full_sha,
        geometry_summary=geom,
    )
    return AdmittedLiveRating(
        label="SECOND_CANDIDATE_R21E",
        full=full,
        compact_r19=None,
        compact_general=compact,
        request=request,
        full_audit=audit,
        full_file_sha256=full_sha,
        snapshot_rel_path=snapshot_rel,
    )
