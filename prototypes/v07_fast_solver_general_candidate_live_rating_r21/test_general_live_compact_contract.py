"""General live compact authority contract (codec only; not a live rating claim)."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from prototypes.v07_fast_solver_general_candidate_live_rating_r21 import (
    general_live_compact_rating as glcr,
)
from prototypes.v07_fast_solver_general_candidate_live_rating_r21.general_live_result_hash import (
    GENERAL_LIVE_RATING_R21_AUTHORITY_ID,
    general_live_rating_result_hash,
    general_live_rating_result_id,
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
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.live_compact_rating import (
    build_live_compact_from_full,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.r19_full_file_audit import file_sha256
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.r19_pinned_identity import (
    R19_FULL_JSON_REL,
)

ROOT = Path(__file__).resolve().parents[2]


def _r21_full_from_r19_codec_fixture() -> tuple[ExperimentalCandidateRatingResult, str]:
    path = ROOT / R19_FULL_JSON_REL
    sha = file_sha256(path)
    full = ExperimentalCandidateRatingResult.model_validate_json(
        path.read_text(encoding="utf-8"),
        strict=True,
    )
    body = full.model_copy(
        update={"experimental_rating_authority_id": GENERAL_LIVE_RATING_R21_AUTHORITY_ID}
    )
    rh = general_live_rating_result_hash(body)
    full_r21 = body.model_copy(
        update={"result_hash": rh, "result_id": general_live_rating_result_id(rh)}
    )
    return full_r21, sha


def test_general_compact_rejects_r19_authority_full() -> None:
    path = ROOT / R19_FULL_JSON_REL
    full = ExperimentalCandidateRatingResult.model_validate_json(
        path.read_text(encoding="utf-8"),
        strict=True,
    )
    request = load_request_from_snapshot_file(ROOT / dict(full.provenance)["snapshot_rel_path"])
    geom = geometry_summary_from_request(request)
    with pytest.raises(glcr.GeneralLiveCompactAuthorityError, match="FULL_AUTHORITY_ID_MISMATCH"):
        glcr.build_general_live_compact_from_full(
            full,
            trajectory_artifact_path=R19_FULL_JSON_REL,
            trajectory_file_sha256=file_sha256(path),
            geometry_summary=geom,
        )


def test_general_compact_build_verify_roundtrip_codec() -> None:
    full, sha = _r21_full_from_r19_codec_fixture()
    request = load_request_from_snapshot_file(ROOT / dict(full.provenance)["snapshot_rel_path"])
    geom = geometry_summary_from_request(request)
    compact = glcr.build_general_live_compact_from_full(
        full,
        trajectory_artifact_path=R19_FULL_JSON_REL,
        trajectory_file_sha256=sha,
        geometry_summary=geom,
    )
    glcr.verify_general_live_compact_against_full(
        compact,
        full,
        full_file_sha256=sha,
        geometry_summary=geom,
    )
    tampered = compact.model_copy(update={"total_duty_w": compact.total_duty_w + Decimal("1")})
    tampered = tampered.model_copy(
        update={"compact_result_hash": glcr.general_live_compact_rating_hash(tampered)}
    )
    with pytest.raises(glcr.GeneralLiveCompactAuthorityError):
        glcr.verify_general_live_compact_against_full(
            tampered,
            full,
            full_file_sha256=sha,
            geometry_summary=geom,
        )


def test_r19_compact_builder_still_accepts_pinned_r19_full() -> None:
    path = ROOT / R19_FULL_JSON_REL
    sha = file_sha256(path)
    full = ExperimentalCandidateRatingResult.model_validate_json(
        path.read_text(encoding="utf-8"),
        strict=True,
    )
    request = load_request_from_snapshot_file(ROOT / dict(full.provenance)["snapshot_rel_path"])
    geom = geometry_summary_from_request(request)
    compact = build_live_compact_from_full(
        full,
        trajectory_artifact_path=R19_FULL_JSON_REL,
        trajectory_file_sha256=sha,
        geometry_summary=geom,
    )
    assert compact.experimental_rating_authority_id != GENERAL_LIVE_RATING_R21_AUTHORITY_ID
