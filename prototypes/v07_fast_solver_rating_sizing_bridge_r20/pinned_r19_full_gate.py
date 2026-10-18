"""Pinned R19 full rating trust gate for experimental sizing adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from prototypes.v07_fast_solver_evidence_gate.trusted_constants import CANDIDATE_B_ID
from prototypes.v07_fast_solver_rating_authority_admission_r11.experimental_models import (
    ExperimentalCandidateRatingResult,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.live_compact_rating import (
    LiveCompactCandidateRating,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.r19_full_file_audit import (
    audit_r19_full_live_rating_file,
    file_sha256,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.r19_pinned_identity import (
    R19_FULL_JSON_REL,
    R19_RESULT_HASH,
    RATING_REQUEST_HASH,
)


class PinnedR19FullGateError(RuntimeError):
    def __init__(self, code: str, *diagnostics: str) -> None:
        self.code = code
        self.diagnostics = diagnostics
        super().__init__(code)


def load_and_verify_pinned_r19_full(
    root: Path,
) -> tuple[ExperimentalCandidateRatingResult, dict[str, Any], str]:
    audit = audit_r19_full_live_rating_file(root)
    if audit["full_rel_path"] != R19_FULL_JSON_REL:
        raise PinnedR19FullGateError("PINNED_FULL_PATH_MISMATCH", audit["full_rel_path"])
    full_path = root / R19_FULL_JSON_REL
    on_disk_sha = file_sha256(full_path)
    if on_disk_sha != audit["full_file_sha256"]:
        raise PinnedR19FullGateError("PINNED_FULL_FILE_SHA256_MISMATCH")
    full = ExperimentalCandidateRatingResult.model_validate_json(
        full_path.read_text(encoding="utf-8"),
        strict=True,
    )
    if full.result_hash != R19_RESULT_HASH:
        raise PinnedR19FullGateError("PINNED_FULL_RESULT_HASH_MISMATCH")
    if full.rating_request_hash != RATING_REQUEST_HASH:
        raise PinnedR19FullGateError("PINNED_RATING_REQUEST_HASH_MISMATCH")
    if full.candidate_id != CANDIDATE_B_ID:
        raise PinnedR19FullGateError("PINNED_CANDIDATE_ID_MISMATCH")
    return full, audit, on_disk_sha


def assert_compact_matches_pinned_r19_full(
    compact: LiveCompactCandidateRating,
    audit: dict[str, Any],
) -> None:
    if compact.full_trajectory_artifact.path != R19_FULL_JSON_REL:
        raise PinnedR19FullGateError("COMPACT_FULL_PATH_NOT_PINNED_R19")
    if compact.full_trajectory_artifact.file_sha256 != audit["full_file_sha256"]:
        raise PinnedR19FullGateError("COMPACT_FULL_SHA256_NOT_PINNED_R19")
    if compact.full_result_hash != audit["full_result_hash"]:
        raise PinnedR19FullGateError("COMPACT_RESULT_HASH_NOT_PINNED_R19")
