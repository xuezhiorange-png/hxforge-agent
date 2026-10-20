"""Independent fail-closed admission gates for experimental_multi_candidate_sizing_from_admitted."""

# ruff: noqa: E501

from __future__ import annotations

from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
    candidate_rating_request_hash,
)
from hexagent.exchangers.shell_tube.task173_integrated_sizing.models import (
    SizingRequirementAuthority,
)
from hexagent.exchangers.shell_tube.task174_hydraulic_orchestration import (
    recompute_task174_result_hash,
)
from prototypes.v07_fast_solver_evidence_gate.trusted_constants import CANDIDATE_B_ID
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.admitted_identity_binding import (
    verify_admitted_pair_identity,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.mandatory_screening import (
    MandatoryScreeningOutcome,
    execute_experimental_mandatory_screening,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.r22_pinned_identity import (
    FROZEN_Q13_CANDIDATE_SPACE_HASH,
    R21E_FULL_JSON_SHA256,
    SECOND_CANDIDATE_ID,
    TASK168_CANDIDATE_SPACE_AUTHORITY_ID,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.rating_pair_admission import (
    AdmittedLiveRating,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.requirement_verification import (
    verify_requirement_canonical_hash,
    verify_trusted_requirement_binding,
)
from prototypes.v07_fast_solver_general_candidate_live_rating_r21 import (
    general_live_compact_rating as glcr,
)
from prototypes.v07_fast_solver_general_candidate_live_rating_r21.general_live_compact_rating import (
    GeneralLiveCompactAuthorityError,
)
from prototypes.v07_fast_solver_general_candidate_live_rating_r21.general_live_result_hash import (
    general_live_rating_result_hash,
)
from prototypes.v07_fast_solver_live_rating_result_r19.live_result_hash import (
    live_rating_result_hash,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.geometry_summary import (
    geometry_summary_from_request,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.live_compact_rating import (
    LiveCompactAuthorityError,
    live_compact_rating_hash,
    verify_live_compact_against_full,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.r19_pinned_identity import (
    R19_FULL_JSON_SHA256,
)


def _failure(code: str, *diagnostics: str) -> tuple[str, tuple[str, ...]]:
    return code, diagnostics


def verify_trusted_requirement_gate(
    requirement: SizingRequirementAuthority,
) -> tuple[str, tuple[str, ...]] | None:
    if not verify_requirement_canonical_hash(requirement):
        return _failure("SIZING_REQUIREMENT_CANONICAL_HASH_MISMATCH")
    trusted_code = verify_trusted_requirement_binding(requirement)
    if trusted_code is not None:
        return _failure(trusted_code)
    return None


def _verify_full_result_hash_replay(
    admitted: AdmittedLiveRating,
) -> tuple[str, tuple[str, ...]] | None:
    full = admitted.full
    if admitted.label == "CANDIDATE_B_R19":
        replay = live_rating_result_hash(full)
    elif admitted.label == "SECOND_CANDIDATE_R21E":
        replay = general_live_rating_result_hash(full)
    else:
        return _failure("UNTRUSTED_ADMITTED_BUNDLE_LABEL", admitted.label)
    if replay != full.result_hash:
        return _failure(
            "FULL_RESULT_HASH_REPLAY_MISMATCH", admitted.label, replay, full.result_hash
        )
    return None


def _verify_trusted_admitted_provenance(
    admitted: AdmittedLiveRating,
) -> tuple[str, tuple[str, ...]] | None:
    if admitted.label == "CANDIDATE_B_R19":
        if admitted.compact_r19 is None or admitted.compact_general is not None:
            return _failure("UNTRUSTED_ADMITTED_BUNDLE_SHAPE", admitted.label)
        if admitted.full_file_sha256 != R19_FULL_JSON_SHA256:
            return _failure("UNTRUSTED_ADMITTED_FULL_FILE_SHA256", admitted.label)
    elif admitted.label == "SECOND_CANDIDATE_R21E":
        if admitted.compact_general is None or admitted.compact_r19 is not None:
            return _failure("UNTRUSTED_ADMITTED_BUNDLE_SHAPE", admitted.label)
        if admitted.full_file_sha256 != R21E_FULL_JSON_SHA256:
            return _failure("UNTRUSTED_ADMITTED_FULL_FILE_SHA256", admitted.label)
    else:
        return _failure("UNTRUSTED_ADMITTED_BUNDLE_LABEL", admitted.label)
    return None


def _verify_request_and_task174_binding(
    admitted: AdmittedLiveRating,
) -> tuple[str, tuple[str, ...]] | None:
    request = admitted.request
    full = admitted.full
    recomputed_request_hash = candidate_rating_request_hash(request)
    if recomputed_request_hash != full.rating_request_hash:
        return _failure(
            "RATING_REQUEST_HASH_REPLAY_MISMATCH",
            admitted.label,
            recomputed_request_hash,
            full.rating_request_hash,
        )
    task174 = request.task174_result
    task174_replay = recompute_task174_result_hash(task174)
    if task174.result_hash != task174_replay:
        return _failure("TASK174_RESULT_HASH_REPLAY_MISMATCH", admitted.label)
    if full.task174_result_hash != task174.result_hash:
        return _failure(
            "FULL_TASK174_RESULT_HASH_BINDING_MISMATCH",
            admitted.label,
            full.task174_result_hash,
            task174.result_hash,
        )
    return None


def _verify_compact_binding(admitted: AdmittedLiveRating) -> tuple[str, tuple[str, ...]] | None:
    geom = geometry_summary_from_request(admitted.request)
    try:
        if admitted.compact_r19 is not None:
            if admitted.compact_r19.compact_result_hash != live_compact_rating_hash(
                admitted.compact_r19
            ):
                return _failure("COMPACT_RESULT_HASH_REPLAY_MISMATCH", admitted.label)
            verify_live_compact_against_full(
                admitted.compact_r19,
                admitted.full,
                full_file_sha256=admitted.full_file_sha256,
                geometry_summary=geom,
            )
        if admitted.compact_general is not None:
            if (
                admitted.compact_general.compact_result_hash
                != glcr.general_live_compact_rating_hash(admitted.compact_general)
            ):
                return _failure("COMPACT_RESULT_HASH_REPLAY_MISMATCH", admitted.label)
            glcr.verify_general_live_compact_against_full(
                admitted.compact_general,
                admitted.full,
                full_file_sha256=admitted.full_file_sha256,
                geometry_summary=geom,
            )
    except LiveCompactAuthorityError as exc:
        return _failure(
            str(exc.args[0]) if exc.args else "COMPACT_FULL_BINDING_FAILED", admitted.label
        )
    except GeneralLiveCompactAuthorityError as exc:
        return _failure(
            str(exc.args[0]) if exc.args else "COMPACT_FULL_BINDING_FAILED", admitted.label
        )
    return None


def _verify_candidate_space(
    requirement: SizingRequirementAuthority, admitted: AdmittedLiveRating
) -> tuple[str, tuple[str, ...]] | None:
    space = admitted.request.candidate_space_hash
    if space != FROZEN_Q13_CANDIDATE_SPACE_HASH:
        return _failure("ADMITTED_CANDIDATE_SPACE_HASH_MISMATCH", space)
    bound_authority, bound_space = requirement.discrete_candidate_authority_ids_and_hashes[0]
    if bound_authority != TASK168_CANDIDATE_SPACE_AUTHORITY_ID:
        return _failure("REQUIREMENT_CANDIDATE_SPACE_AUTHORITY_ID_MISMATCH", bound_authority)
    if bound_space != FROZEN_Q13_CANDIDATE_SPACE_HASH:
        return _failure("REQUIREMENT_CANDIDATE_SPACE_HASH_MISMATCH", bound_space)
    return None


def _verify_pair_roles(
    admitted: tuple[AdmittedLiveRating, ...],
) -> tuple[str, tuple[str, ...]] | None:
    first, second = admitted[0], admitted[1]
    if first.label != "CANDIDATE_B_R19" or second.label != "SECOND_CANDIDATE_R21E":
        return _failure(
            "ADMITTED_PAIR_ROLE_ORDER_MISMATCH",
            first.label,
            second.label,
        )
    if first.full.candidate_id != CANDIDATE_B_ID:
        return _failure("ADMITTED_CANDIDATE_B_ID_MISMATCH", first.full.candidate_id)
    if second.full.candidate_id != SECOND_CANDIDATE_ID:
        return _failure("ADMITTED_SECOND_CANDIDATE_ID_MISMATCH", second.full.candidate_id)
    if first.request.candidate_id == second.request.candidate_id:
        return _failure("DUPLICATE_CANDIDATE_ID", first.request.candidate_id)
    return None


def verify_mandatory_screening_outcome(
    admitted: tuple[AdmittedLiveRating, ...],
    requirement: SizingRequirementAuthority,
    screening: MandatoryScreeningOutcome | None,
) -> tuple[MandatoryScreeningOutcome | None, tuple[str, tuple[str, ...]] | None]:
    expected = execute_experimental_mandatory_screening(admitted, requirement)
    if screening is None:
        return expected, None
    if (
        screening.mandatory_screening_gate != expected.mandatory_screening_gate
        or screening.mandatory_screening_complete != expected.mandatory_screening_complete
        or screening.production_recommendation_authorized
        != expected.production_recommendation_authorized
        or screening.fiv_authority_status != expected.fiv_authority_status
        or screening.screening_gap_codes != expected.screening_gap_codes
    ):
        return None, _failure("FORGED_MANDATORY_SCREENING_OUTCOME")
    return screening, None


def verify_independent_consumer_admission(
    requirement: SizingRequirementAuthority,
    admitted: tuple[AdmittedLiveRating, ...],
    *,
    screening: MandatoryScreeningOutcome | None = None,
) -> tuple[MandatoryScreeningOutcome | None, tuple[str, tuple[str, ...]] | None]:
    if len(admitted) != 2:
        return None, _failure("ADMITTED_CANDIDATE_COUNT_INVALID", str(len(admitted)))

    failure = verify_trusted_requirement_gate(requirement)
    if failure is not None:
        return None, failure

    for item in admitted:
        failure = _verify_trusted_admitted_provenance(item)
        if failure is not None:
            return None, failure

    failure = _verify_pair_roles(admitted)
    if failure is not None:
        return None, failure

    failure = verify_admitted_pair_identity(admitted)
    if failure is not None:
        return None, failure

    for item in admitted:
        for step in (
            lambda i=item: _verify_full_result_hash_replay(i),
            lambda i=item: _verify_request_and_task174_binding(i),
            lambda i=item: _verify_compact_binding(i),
            lambda i=item: _verify_candidate_space(requirement, i),
        ):
            failure = step()
            if failure is not None:
                return None, failure

    return verify_mandatory_screening_outcome(admitted, requirement, screening)
