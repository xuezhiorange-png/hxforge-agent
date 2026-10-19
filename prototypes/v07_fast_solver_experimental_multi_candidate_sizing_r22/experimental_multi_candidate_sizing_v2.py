"""R22A v2 wrapper preserving immutable R22 v1 sizing identity."""

# ruff: noqa: E501

from __future__ import annotations

from pathlib import Path

from hexagent.exchangers.shell_tube.task173_integrated_sizing.models import (
    SizingRequirementAuthority,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.experimental_multi_candidate_sizing import (
    experimental_multi_candidate_sizing,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.experimental_sizing_requirement import (
    experimental_multi_candidate_sizing_requirement,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.mandatory_screening import (
    MandatoryScreeningOutcome,
    execute_experimental_mandatory_screening,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.rating_pair_admission import (
    RatingAdmissionError,
    admit_candidate_b_live_rating,
    admit_second_candidate_live_rating,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.result_models_v2 import (
    ExperimentalMultiCandidateSizingResultV2,
    experimental_multi_candidate_sizing_result_v2_hash,
    experimental_multi_candidate_sizing_result_v2_id,
)


def _screening_for_v1(
    root: Path,
    requirement: SizingRequirementAuthority,
    v1_blocked: bool,
) -> MandatoryScreeningOutcome:
    if v1_blocked:
        return execute_experimental_mandatory_screening((), requirement)
    try:
        admitted = (admit_candidate_b_live_rating(root), admit_second_candidate_live_rating(root))
    except RatingAdmissionError:
        return execute_experimental_mandatory_screening((), requirement)
    return execute_experimental_mandatory_screening(admitted, requirement)


def build_experimental_multi_candidate_sizing_v2(
    root: Path,
    requirement: SizingRequirementAuthority | None = None,
) -> ExperimentalMultiCandidateSizingResultV2:
    req = requirement or experimental_multi_candidate_sizing_requirement()
    v1 = experimental_multi_candidate_sizing(root, req)
    screening = _screening_for_v1(root, req, v1.status == "BLOCKED")

    envelope = ExperimentalMultiCandidateSizingResultV2(
        v1_result=v1,
        mandatory_screening_gate=screening.mandatory_screening_gate,
        fiv_authority_status=screening.fiv_authority_status,
        screening_rule_records=screening.rule_records,
        screening_gap_codes=screening.screening_gap_codes,
        experimental_recommended_candidate_id=v1.recommended_candidate_id,
        experimental_alternative_candidate_ids=v1.alternative_candidate_ids,
        result_hash="0" * 64,
        result_id="pending",
    )
    digest = experimental_multi_candidate_sizing_result_v2_hash(envelope)
    return envelope.model_copy(
        update={
            "result_hash": digest,
            "result_id": experimental_multi_candidate_sizing_result_v2_id(digest),
        }
    )
