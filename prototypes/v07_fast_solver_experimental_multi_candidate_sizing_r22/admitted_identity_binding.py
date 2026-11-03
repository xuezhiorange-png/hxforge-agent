"""Fail-closed identity binding for AdmittedLiveRating bundles."""

# ruff: noqa: E501

from __future__ import annotations

from prototypes.v07_fast_solver_evidence_gate.trusted_constants import CANDIDATE_B_ID
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.r22_pinned_identity import (
    SECOND_CANDIDATE_ID,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.rating_pair_admission import (
    AdmittedLiveRating,
)


def verify_admitted_live_rating_identity(admitted: AdmittedLiveRating) -> str | None:
    request = admitted.request
    full = admitted.full
    if request.candidate_id != full.candidate_id:
        return "ADMITTED_REQUEST_CANDIDATE_ID_BINDING_MISMATCH"
    if request.candidate_hash != full.candidate_hash:
        return "ADMITTED_REQUEST_CANDIDATE_HASH_BINDING_MISMATCH"
    if admitted.compact_r19 is not None:
        compact = admitted.compact_r19
        if compact.candidate_id != full.candidate_id:
            return "ADMITTED_COMPACT_CANDIDATE_ID_BINDING_MISMATCH"
        if compact.candidate_hash != full.candidate_hash:
            return "ADMITTED_COMPACT_CANDIDATE_HASH_BINDING_MISMATCH"
    if admitted.compact_general is not None:
        compact = admitted.compact_general
        if compact.candidate_id != full.candidate_id:
            return "ADMITTED_COMPACT_CANDIDATE_ID_BINDING_MISMATCH"
        if compact.candidate_hash != full.candidate_hash:
            return "ADMITTED_COMPACT_CANDIDATE_HASH_BINDING_MISMATCH"
    if admitted.label == "CANDIDATE_B_R19" and full.candidate_id != CANDIDATE_B_ID:
        return "ADMITTED_PINNED_CANDIDATE_ID_MISMATCH"
    if admitted.label == "SECOND_CANDIDATE_R21E" and full.candidate_id != SECOND_CANDIDATE_ID:
        return "ADMITTED_PINNED_CANDIDATE_ID_MISMATCH"
    return None


def verify_admitted_pair_identity(
    admitted: tuple[AdmittedLiveRating, ...],
) -> tuple[str, tuple[str, ...]] | None:
    for item in admitted:
        code = verify_admitted_live_rating_identity(item)
        if code is not None:
            return code, (item.label, item.request.candidate_id, item.full.candidate_id)
    return None
