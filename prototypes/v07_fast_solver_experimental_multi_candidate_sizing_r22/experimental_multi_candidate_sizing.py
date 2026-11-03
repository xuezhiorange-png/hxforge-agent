"""Experimental multi-candidate sizing consumer for verified live ratings."""

# ruff: noqa: E501

from __future__ import annotations

from pathlib import Path
from typing import Literal

from hexagent.exchangers.shell_tube.task173_integrated_sizing.models import (
    RANKING_POLICY_HASH,
    RANKING_POLICY_ID,
    SizingRequirementAuthority,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.experimental_sizing_requirement import (
    experimental_multi_candidate_sizing_requirement,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.independent_consumer_admission import (
    verify_independent_consumer_admission,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.mandatory_screening import (
    MandatoryScreeningOutcome,
    execute_experimental_mandatory_screening,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.r22_pinned_identity import (
    FROZEN_Q13_CANDIDATE_SPACE_HASH,
    TASK168_CANDIDATE_SPACE_AUTHORITY_ID,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.ranking import (
    compute_ranking_score,
    rank_experimental_candidates,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.rating_pair_admission import (
    AdmittedLiveRating,
    RatingAdmissionError,
    admit_candidate_b_live_rating,
    admit_second_candidate_live_rating,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.requirement_verification import (
    verify_requirement_canonical_hash,
    verify_trusted_requirement_binding,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.result_models import (
    ExperimentalCandidateSizingRecord,
    ExperimentalMultiCandidateSizingResult,
    experimental_multi_candidate_sizing_result_hash,
    experimental_multi_candidate_sizing_result_id,
)

_SCREENING_DEFERRED_WARN = "MANDATORY_SCREENING_POLICY_NOT_REEXECUTED_LIVE_EXPERIMENTAL_PATH"
_FIV_WARN = "FIV_NUMERIC_LIMIT_AUTHORITY_MISSING"


def _construction_family_pass(
    request_dimensions: tuple[tuple[str, str], ...],
    allowed: tuple[str, ...],
) -> bool:
    family = dict(request_dimensions).get("CONSTRUCTION_FAMILY")
    return family in allowed if family else False


def _evaluate_candidate(
    admitted: AdmittedLiveRating,
    requirement: SizingRequirementAuthority,
) -> ExperimentalCandidateSizingRecord:
    request = admitted.request
    full = admitted.full
    task174 = request.task174_result
    tube_dp = task174.modeled_total_tube_side_pressure_drop_pa
    shell_dp = task174.bell_total_shell_pressure_drop_pa
    rated_duty = full.total_duty_w
    duty_pass = rated_duty >= requirement.required_duty_w
    tube_pass = tube_dp <= requirement.max_tube_dp_pa
    shell_pass = shell_dp <= requirement.max_shell_dp_pa
    blockers = tuple(
        code
        for code, passed in (
            ("DUTY_BELOW_REQUIRED", duty_pass),
            ("TUBE_DP_ABOVE_MAXIMUM", tube_pass),
            ("SHELL_DP_ABOVE_MAXIMUM", shell_pass),
            (
                "CONSTRUCTION_FAMILY_NOT_ALLOWED",
                _construction_family_pass(
                    request.selected_dimensions,
                    requirement.allowed_construction_families,
                ),
            ),
        )
        if not passed
    )
    warnings: list[str] = [_SCREENING_DEFERRED_WARN]
    if task174.fiv_numeric_limit_authority_missing:
        warnings.append(_FIV_WARN)
    warnings_tuple = tuple(sorted(set(warnings), key=lambda s: s.encode("utf-8")))
    if blockers:
        status: Literal["PASS", "WARN", "BLOCKED"] = "BLOCKED"
        screening_status: Literal["WARN", "BLOCKED"] = "BLOCKED"
        score = None
    else:
        status = "WARN" if warnings_tuple else "PASS"
        screening_status = "WARN"
        score = compute_ranking_score(shell_dp, "WARN" if warnings_tuple else "PASS")

    compact_hash = (
        admitted.compact_r19.compact_result_hash
        if admitted.compact_r19 is not None
        else admitted.compact_general.compact_result_hash  # type: ignore[union-attr]
    )
    return ExperimentalCandidateSizingRecord(
        candidate_id=request.candidate_id,
        candidate_hash=request.candidate_hash,
        rating_request_hash=full.rating_request_hash,
        full_result_hash=full.result_hash,
        compact_result_hash=compact_hash,
        experimental_rating_authority_id=full.experimental_rating_authority_id,
        rated_duty_w=rated_duty,
        tube_dp_pa=tube_dp,
        shell_dp_pa=shell_dp,
        duty_constraint="PASS" if duty_pass else "BLOCKED",
        tube_dp_constraint="PASS" if tube_pass else "BLOCKED",
        shell_dp_constraint="PASS" if shell_pass else "BLOCKED",
        screening_status=screening_status,
        status=status,
        warnings=warnings_tuple,
        blockers=blockers,
        ranking_score=score,
    )


def _blocked_result(
    requirement: SizingRequirementAuthority,
    *,
    code: str,
    diagnostics: tuple[str, ...],
    records: tuple[ExperimentalCandidateSizingRecord, ...] = (),
) -> ExperimentalMultiCandidateSizingResult:
    result = ExperimentalMultiCandidateSizingResult(
        status="BLOCKED",
        numerical_authority_status="CANDIDATE",
        sizing_requirement_hash=requirement.canonical_hash,
        candidate_space_hash=FROZEN_Q13_CANDIDATE_SPACE_HASH,
        candidate_space_authority_id=TASK168_CANDIDATE_SPACE_AUTHORITY_ID,
        candidate_count=len(records),
        candidate_records=records,
        ranking_trace_status="NOT_APPLICABLE",
        mandatory_screening_gate="NOT_EVALUATED",
        duty_constraint_gate="BLOCKED",
        tube_dp_constraint_gate="BLOCKED",
        shell_dp_constraint_gate="BLOCKED",
        candidate_identity_gate="BLOCKED",
        blocked_code=code,
        blocked_diagnostics=diagnostics,
        result_provenance=(("blocked_code", code),),
        result_hash="0" * 64,
        result_id="blocked",
    )
    digest = experimental_multi_candidate_sizing_result_hash(result)
    return result.model_copy(
        update={
            "result_hash": digest,
            "result_id": experimental_multi_candidate_sizing_result_id(digest),
        }
    )


def experimental_multi_candidate_sizing_from_admitted(
    requirement: SizingRequirementAuthority,
    admitted: tuple[AdmittedLiveRating, ...],
    *,
    evidence_root: Path | None = None,
    screening: MandatoryScreeningOutcome | None = None,
) -> ExperimentalMultiCandidateSizingResult:
    screening, admission_failure = verify_independent_consumer_admission(
        requirement,
        admitted,
        evidence_root=evidence_root,
        screening=screening,
    )
    if admission_failure is not None:
        code, diagnostics = admission_failure
        return _blocked_result(requirement, code=code, diagnostics=diagnostics)
    assert screening is not None
    screening_gate = screening.mandatory_screening_gate

    candidate_b = admitted[0]
    second = admitted[1]

    records = [
        _evaluate_candidate(candidate_b, requirement),
        _evaluate_candidate(second, requirement),
    ]
    duty_gate = "PASS" if all(r.duty_constraint == "PASS" for r in records) else "BLOCKED"
    tube_gate = "PASS" if all(r.tube_dp_constraint == "PASS" for r in records) else "BLOCKED"
    shell_gate = "PASS" if all(r.shell_dp_constraint == "PASS" for r in records) else "BLOCKED"
    if any(r.status == "BLOCKED" for r in records):
        result = ExperimentalMultiCandidateSizingResult(
            status="RANKING_BLOCKED",
            numerical_authority_status="CANDIDATE",
            sizing_requirement_hash=requirement.canonical_hash,
            candidate_space_hash=FROZEN_Q13_CANDIDATE_SPACE_HASH,
            candidate_space_authority_id=TASK168_CANDIDATE_SPACE_AUTHORITY_ID,
            candidate_count=len(records),
            candidate_records=tuple(records),
            ranking_trace_status="RANKING_BLOCKED",
            mandatory_screening_gate=screening_gate,
            duty_constraint_gate=duty_gate,
            tube_dp_constraint_gate=tube_gate,
            shell_dp_constraint_gate=shell_gate,
            candidate_identity_gate="PASS",
            blocked_code="CANDIDATE_ENGINEERING_CONSTRAINT_BLOCKED",
            blocked_diagnostics=tuple(
                f"{r.candidate_id}:{','.join(r.blockers)}" for r in records if r.blockers
            ),
            result_provenance=(
                ("ranking_policy_id", RANKING_POLICY_ID),
                ("ranking_policy_hash", RANKING_POLICY_HASH),
            ),
            result_hash="0" * 64,
            result_id="pending",
        )
        digest = experimental_multi_candidate_sizing_result_hash(result)
        return result.model_copy(
            update={
                "result_hash": digest,
                "result_id": experimental_multi_candidate_sizing_result_id(digest),
            }
        )

    ranked_records, trace = rank_experimental_candidates(records)
    ranked_ids = tuple(r.candidate_id for r in sorted(ranked_records, key=lambda x: x.rank or 999))
    recommended = ranked_ids[0] if ranked_ids else None
    alternatives = ranked_ids[1:]

    result = ExperimentalMultiCandidateSizingResult(
        status="EXPERIMENTAL_COMPLETE",
        numerical_authority_status="CANDIDATE",
        sizing_requirement_hash=requirement.canonical_hash,
        candidate_space_hash=FROZEN_Q13_CANDIDATE_SPACE_HASH,
        candidate_space_authority_id=TASK168_CANDIDATE_SPACE_AUTHORITY_ID,
        candidate_count=len(ranked_records),
        candidate_records=tuple(ranked_records),
        ranking_trace=trace,
        ranking_trace_status="COMPLETE",
        recommended_candidate_id=recommended,
        alternative_candidate_ids=alternatives,
        mandatory_screening_gate=screening_gate,
        duty_constraint_gate=duty_gate,
        tube_dp_constraint_gate=tube_gate,
        shell_dp_constraint_gate=shell_gate,
        candidate_identity_gate="PASS",
        result_provenance=(
            ("consumer", "experimental_multi_candidate_sizing.v1"),
            ("ranking_policy_id", RANKING_POLICY_ID),
            ("ranking_policy_hash", RANKING_POLICY_HASH),
            ("candidate_b_full_sha256", candidate_b.full_file_sha256),
            ("second_candidate_full_sha256", second.full_file_sha256),
        ),
        result_hash="0" * 64,
        result_id="pending",
    )
    digest = experimental_multi_candidate_sizing_result_hash(result)
    final = result.model_copy(
        update={
            "result_hash": digest,
            "result_id": experimental_multi_candidate_sizing_result_id(digest),
        }
    )
    if digest != experimental_multi_candidate_sizing_result_hash(final):
        return _blocked_result(
            requirement,
            code="SIZING_RESULT_HASH_REPLAY_FAILED",
            diagnostics=(),
            records=tuple(ranked_records),
        )
    return final


def experimental_multi_candidate_sizing(
    root: Path,
    requirement: SizingRequirementAuthority | None = None,
) -> ExperimentalMultiCandidateSizingResult:
    requirement = requirement or experimental_multi_candidate_sizing_requirement()
    if not verify_requirement_canonical_hash(requirement):
        return _blocked_result(
            requirement,
            code="SIZING_REQUIREMENT_CANONICAL_HASH_MISMATCH",
            diagnostics=(),
        )
    trusted_code = verify_trusted_requirement_binding(requirement)
    if trusted_code is not None:
        return _blocked_result(
            requirement,
            code=trusted_code,
            diagnostics=(),
        )

    try:
        candidate_b = admit_candidate_b_live_rating(root)
        second = admit_second_candidate_live_rating(root)
    except RatingAdmissionError as exc:
        return _blocked_result(
            requirement,
            code=exc.code,
            diagnostics=exc.diagnostics,
        )

    admitted = (candidate_b, second)
    screening = execute_experimental_mandatory_screening(admitted, requirement)
    return experimental_multi_candidate_sizing_from_admitted(
        requirement,
        admitted,
        evidence_root=root,
        screening=screening,
    )
