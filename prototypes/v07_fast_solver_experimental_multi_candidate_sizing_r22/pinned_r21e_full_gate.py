"""Pinned R21E general full rating trust gate."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.r22_pinned_identity import (
    R21E_FULL_GIT_BLOB,
    R21E_FULL_JSON_REL,
    R21E_FULL_JSON_SHA256,
    R21E_RESULT_HASH,
    R21E_SOURCE_COMMIT,
    SECOND_CANDIDATE_ID,
    SECOND_RATING_REQUEST_HASH,
)
from prototypes.v07_fast_solver_general_candidate_live_rating_r21.general_live_result_hash import (
    GENERAL_LIVE_RATING_R21_AUTHORITY_ID,
    general_live_rating_result_hash,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.experimental_models import (
    ExperimentalCandidateRatingResult,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.r19_full_file_audit import (
    file_sha256,
    git_blob_id,
    git_blob_sha256,
)


class PinnedR21eFullGateError(RuntimeError):
    def __init__(self, code: str, *diagnostics: str) -> None:
        self.code = code
        self.diagnostics = diagnostics
        super().__init__(code)


def audit_r21e_full_live_rating_file(root: Path) -> dict[str, Any]:
    full_path = root / R21E_FULL_JSON_REL
    if not full_path.is_file():
        raise PinnedR21eFullGateError("R21E_FULL_FILE_MISSING", R21E_FULL_JSON_REL)
    on_disk_sha = file_sha256(full_path)
    if on_disk_sha != R21E_FULL_JSON_SHA256:
        raise PinnedR21eFullGateError(
            "R21E_FULL_FILE_SHA256_MISMATCH",
            on_disk_sha,
            R21E_FULL_JSON_SHA256,
        )
    blob_id = git_blob_id(root, R21E_SOURCE_COMMIT, R21E_FULL_JSON_REL)
    if blob_id != R21E_FULL_GIT_BLOB:
        raise PinnedR21eFullGateError("R21E_FULL_GIT_BLOB_ID_MISMATCH", blob_id, R21E_FULL_GIT_BLOB)
    blob_sha = git_blob_sha256(root, R21E_SOURCE_COMMIT, R21E_FULL_JSON_REL)
    if blob_sha != R21E_FULL_JSON_SHA256:
        raise PinnedR21eFullGateError("R21E_GIT_BLOB_CONTENT_SHA_MISMATCH", blob_sha)

    full = ExperimentalCandidateRatingResult.model_validate_json(
        full_path.read_text(encoding="utf-8"),
        strict=True,
    )
    recomputed = general_live_rating_result_hash(full)
    if recomputed != R21E_RESULT_HASH or full.result_hash != R21E_RESULT_HASH:
        raise PinnedR21eFullGateError("R21E_RESULT_HASH_REPLAY_MISMATCH")
    if full.experimental_rating_authority_id != GENERAL_LIVE_RATING_R21_AUTHORITY_ID:
        raise PinnedR21eFullGateError("R21E_AUTHORITY_ID_MISMATCH")
    if full.rating_request_hash != SECOND_RATING_REQUEST_HASH:
        raise PinnedR21eFullGateError("R21E_RATING_REQUEST_HASH_MISMATCH")
    if full.candidate_id != SECOND_CANDIDATE_ID:
        raise PinnedR21eFullGateError("R21E_CANDIDATE_ID_MISMATCH")
    if full.execution_mode != "LIVE_NUMERICAL_SOLVE":
        raise PinnedR21eFullGateError("R21E_EXECUTION_MODE_NOT_LIVE")
    if full.numerical_authority_status != "CANDIDATE":
        raise PinnedR21eFullGateError("R21E_NUMERICAL_AUTHORITY_NOT_CANDIDATE")
    if full.mesh_sequence_gate != "PASS" or not full.strict_replay_pass:
        raise PinnedR21eFullGateError("R21E_MESH_GATE_NOT_PASS")

    return {
        "r21e_source_commit": R21E_SOURCE_COMMIT,
        "full_rel_path": R21E_FULL_JSON_REL,
        "full_file_sha256": on_disk_sha,
        "full_git_blob_id": blob_id,
        "full_git_blob_content_sha256": blob_sha,
        "full_result_hash": full.result_hash,
        "full_result_hash_recomputed": recomputed,
        "accepted_mesh_result_hash": full.accepted_mesh_result_hash,
        "headroom_mesh_result_hash": full.headroom_mesh_result_hash,
        "task174_result_hash": full.task174_result_hash,
    }


def load_and_verify_pinned_r21e_full(
    root: Path,
) -> tuple[ExperimentalCandidateRatingResult, dict[str, Any], str]:
    audit = audit_r21e_full_live_rating_file(root)
    full_path = root / R21E_FULL_JSON_REL
    full = ExperimentalCandidateRatingResult.model_validate_json(
        full_path.read_text(encoding="utf-8"),
        strict=True,
    )
    return full, audit, audit["full_file_sha256"]
