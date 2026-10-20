"""Bind independent consumer inputs to re-read frozen R19/R21E evidence on disk."""

# ruff: noqa: E501

from __future__ import annotations

from pathlib import Path

from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
    CandidateRatingRequest,
    candidate_rating_request_hash,
)
from hexagent.exchangers.shell_tube.task174_hydraulic_orchestration import (
    recompute_task174_result_hash,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.pinned_r21e_full_gate import (
    load_and_verify_pinned_r21e_full,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.r22_pinned_identity import (
    FROZEN_Q13_CANDIDATE_SPACE_HASH,
    R21E_FULL_JSON_REL,
    R21E_FULL_JSON_SHA256,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.rating_pair_admission import (
    AdmittedLiveRating,
    _load_r21e_compact,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.native_codec import (
    native_projection,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.request_snapshot import (
    load_request_from_snapshot_file,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.experimental_sizing_rating_adapter import (
    load_verified_live_compact_from_r19_audit,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.pinned_r19_full_gate import (
    load_and_verify_pinned_r19_full,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.r19_full_file_audit import (
    file_sha256,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.r19_pinned_identity import (
    R19_FULL_JSON_REL,
    R19_FULL_JSON_SHA256,
)


def _fail(code: str, *diagnostics: str) -> tuple[str, tuple[str, ...]]:
    return code, diagnostics


def _json_projection(model: object) -> dict[str, object]:
    return model.model_dump(mode="json")  # type: ignore[union-attr]


def _load_trusted_r19_bundle(root: Path) -> tuple[AdmittedLiveRating, str]:
    full, _audit, disk_sha = load_and_verify_pinned_r19_full(root)
    compact, _ = load_verified_live_compact_from_r19_audit(root)
    snapshot_rel = str(dict(full.provenance).get("snapshot_rel_path") or "")
    if not snapshot_rel:
        raise ValueError("R19_MISSING_SNAPSHOT_PROVENANCE")
    request = load_request_from_snapshot_file(root / snapshot_rel)
    trusted = AdmittedLiveRating(
        label="CANDIDATE_B_R19",
        full=full,
        compact_r19=compact,
        compact_general=None,
        request=request,
        full_audit={},
        full_file_sha256=disk_sha,
        snapshot_rel_path=snapshot_rel,
    )
    return trusted, disk_sha


def _load_trusted_r21e_bundle(root: Path) -> tuple[AdmittedLiveRating, str]:
    full, _audit, disk_sha = load_and_verify_pinned_r21e_full(root)
    compact = _load_r21e_compact(root)
    snapshot_rel = str(dict(full.provenance).get("snapshot_rel_path") or "")
    if not snapshot_rel:
        raise ValueError("R21E_MISSING_SNAPSHOT_PROVENANCE")
    request = load_request_from_snapshot_file(root / snapshot_rel)
    trusted = AdmittedLiveRating(
        label="SECOND_CANDIDATE_R21E",
        full=full,
        compact_r19=None,
        compact_general=compact,
        request=request,
        full_audit={},
        full_file_sha256=disk_sha,
        snapshot_rel_path=snapshot_rel,
    )
    return trusted, disk_sha


def _verify_task171_task174_upstream(request: CandidateRatingRequest, label: str) -> str | None:
    t174 = request.task174_result
    if t174.result_hash != recompute_task174_result_hash(t174):
        return "TASK174_RESULT_HASH_REPLAY_MISMATCH"
    if request.candidate_space_hash != FROZEN_Q13_CANDIDATE_SPACE_HASH:
        return "ADMITTED_CANDIDATE_SPACE_HASH_MISMATCH"
    _ = candidate_rating_request_hash(request)
    return None


def verify_immutable_pinned_evidence(
    root: Path | None,
    admitted: AdmittedLiveRating,
) -> tuple[str, tuple[str, ...]] | None:
    if root is None:
        return _fail("UNTRUSTED_EVIDENCE_ROOT_MISSING")
    if admitted.label == "CANDIDATE_B_R19":
        rel_full = R19_FULL_JSON_REL
        expected_sha = R19_FULL_JSON_SHA256
        try:
            trusted, disk_sha = _load_trusted_r19_bundle(root)
        except Exception as exc:  # noqa: BLE001
            return _fail("PINNED_R19_EVIDENCE_READ_FAILED", str(exc))
    elif admitted.label == "SECOND_CANDIDATE_R21E":
        rel_full = R21E_FULL_JSON_REL
        expected_sha = R21E_FULL_JSON_SHA256
        try:
            trusted, disk_sha = _load_trusted_r21e_bundle(root)
        except Exception as exc:  # noqa: BLE001
            return _fail("PINNED_R21E_EVIDENCE_READ_FAILED", str(exc))
    else:
        return _fail("UNTRUSTED_ADMITTED_BUNDLE_LABEL", admitted.label)

    on_disk_sha = file_sha256(root / rel_full)
    if on_disk_sha != expected_sha:
        return _fail("PINNED_FULL_FILE_SHA256_MISMATCH", rel_full, on_disk_sha, expected_sha)
    if admitted.full_file_sha256 != on_disk_sha:
        return _fail(
            "FORGED_FULL_FILE_SHA256_DECLARATION",
            admitted.label,
            admitted.full_file_sha256,
            on_disk_sha,
        )

    if _json_projection(admitted.full) != _json_projection(trusted.full):
        return _fail("PINNED_FULL_STRUCTURAL_MISMATCH", admitted.label)
    if native_projection(admitted.request) != native_projection(trusted.request):
        return _fail("PINNED_REQUEST_STRUCTURAL_MISMATCH", admitted.label)
    if candidate_rating_request_hash(admitted.request) != candidate_rating_request_hash(
        trusted.request
    ):
        return _fail("RATING_REQUEST_HASH_REPLAY_MISMATCH", admitted.label)
    if admitted.snapshot_rel_path != trusted.snapshot_rel_path:
        return _fail(
            "PINNED_SNAPSHOT_PATH_MISMATCH",
            admitted.snapshot_rel_path,
            trusted.snapshot_rel_path,
        )

    if admitted.compact_r19 is not None:
        if trusted.compact_r19 is None:
            return _fail("PINNED_COMPACT_SHAPE_MISMATCH", admitted.label)
        if _json_projection(admitted.compact_r19) != _json_projection(trusted.compact_r19):
            return _fail("PINNED_COMPACT_STRUCTURAL_MISMATCH", admitted.label)
    if admitted.compact_general is not None:
        if trusted.compact_general is None:
            return _fail("PINNED_COMPACT_SHAPE_MISMATCH", admitted.label)
        if _json_projection(admitted.compact_general) != _json_projection(trusted.compact_general):
            return _fail("PINNED_COMPACT_STRUCTURAL_MISMATCH", admitted.label)

    upstream = _verify_task171_task174_upstream(admitted.request, admitted.label)
    if upstream is not None:
        return _fail(upstream, admitted.label)

    if admitted.full.task174_result_hash != admitted.request.task174_result.result_hash:
        return _fail(
            "FULL_TASK174_RESULT_HASH_BINDING_MISMATCH",
            admitted.label,
            admitted.full.task174_result_hash,
            admitted.request.task174_result.result_hash,
        )
    return None
