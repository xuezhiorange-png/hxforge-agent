"""Experimental Task168 → Task174 → native rating candidate selection (no fixed IDs)."""

# ruff: noqa: E501

from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Any, cast

from hexagent.exchangers.shell_tube.bell_delaware.models import Task166BlockedResult, Task166Result
from hexagent.exchangers.shell_tube.manufacturable_candidates import service as task168
from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import candidate_space_hash
from hexagent.exchangers.shell_tube.task173_integrated_sizing.candidate_materialization import (
    materialize_candidate_task171,
)
from hexagent.exchangers.shell_tube.task173_integrated_sizing.service import (
    DIMENSION_ORDER,
    _candidate_rating_request,
    _candidate_request_for_task174,
    validate_task174_candidate,
)
from hexagent.exchangers.shell_tube.task174_hydraulic_orchestration import (
    Task174NativeOutputs,
    Task174SuccessResult,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.sizing_request_builder import (
    build_task173_sizing_request,
)


@dataclass(frozen=True)
class CandidateSelectionRecord:
    candidate_id: str
    candidate_hash: str
    structural_admitted: bool
    task168_chain_status: str
    task168_blocked_stage: str | None
    task168_blocked_codes: tuple[str, ...]
    task174_status: str
    rating_request_ready: bool
    rating_request_hash: str | None
    task171_result_hash: str | None
    task174_result_hash: str | None
    selected_for_rating: bool


@dataclass(frozen=True)
class CandidateSelectionOutcome:
    status: str
    candidate_space_hash: str
    selected_candidate_id: str | None
    selected_rating_request_hash: str | None
    records: tuple[CandidateSelectionRecord, ...]
    selection_reason: str | None


def enumerate_experimental_rating_candidates(case: EngineeringCase) -> CandidateSelectionOutcome:
    """Enumerate candidates and pick the first rating-ready row under MVP experimental policy."""
    sizing_req = build_task173_sizing_request(case)
    t168 = sizing_req.task168_candidate_request
    authorities = task168._authority_map(t168)
    dimensions = tuple(
        task168._sort_values(authorities[role].values)
        for role in DIMENSION_ORDER
        if role != "SHELL_GEOMETRY_ID"
    )
    space_hash = candidate_space_hash(t168, t168.discrete_candidate_set_authorities)
    digest = sizing_req.requirement_authority.canonical_hash
    from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
        candidate_rating_request_hash,
    )

    records: list[CandidateSelectionRecord] = []
    selected_id: str | None = None
    selected_rating_hash: str | None = None
    selection_reason: str | None = None

    for combination in itertools.product(t168.shell_geometry_catalog.records, *dimensions):
        candidate = task168._candidate(t168, authorities, combination[0], tuple(combination[1:]))
        structural_blockers = task168._structural_blockers(candidate)
        if structural_blockers:
            blocker_codes = tuple(str(item.code) for item in structural_blockers)
            records.append(
                CandidateSelectionRecord(
                    candidate_id=candidate.candidate_id,
                    candidate_hash=candidate.candidate_hash,
                    structural_admitted=False,
                    task168_chain_status="BLOCKED_STRUCTURAL",
                    task168_blocked_stage="TASK168_STRUCTURAL",
                    task168_blocked_codes=blocker_codes,
                    task174_status="NOT_RUN",
                    rating_request_ready=False,
                    rating_request_hash=None,
                    task171_result_hash=None,
                    task174_result_hash=None,
                    selected_for_rating=False,
                )
            )
            continue

        bundle, stage_failure, _ = task168._execute_candidate_chain(
            t168,
            candidate,
            combination[0],
            include_legacy_task162=False,
            include_legacy_task168_rating_dependencies=False,
            preserve_baffle_orientation_sequence=False,
        )
        if stage_failure is not None:
            records.append(
                CandidateSelectionRecord(
                    candidate_id=candidate.candidate_id,
                    candidate_hash=candidate.candidate_hash,
                    structural_admitted=True,
                    task168_chain_status="BLOCKED_DOWNSTREAM",
                    task168_blocked_stage=str(stage_failure.stage),
                    task168_blocked_codes=(str(stage_failure.code),),
                    task174_status="NOT_RUN",
                    rating_request_ready=False,
                    rating_request_hash=None,
                    task171_result_hash=None,
                    task174_result_hash=None,
                    selected_for_rating=False,
                )
            )
            continue

        topology = materialize_candidate_task171(
            candidate=candidate,
            configuration=bundle.task020_configuration,
            layout=bundle.task021_layout,
            bundle_geometry=bundle.task022_geometry,
            baffle_geometry=bundle.task024_geometry,
            task025_result=bundle.task025_result,
            task024_request=bundle.task024_request,
            task025_request=bundle.task025_request,
        )
        t174_req = _candidate_request_for_task174(candidate, bundle, topology)
        t174 = validate_task174_candidate(
            t174_req,
            Task174NativeOutputs(
                task029=bundle.task029_result,
                task034=None,
                task166=cast(Task166Result | Task166BlockedResult | None, bundle.task166_result),
            ),
        )
        if type(t174) is not Task174SuccessResult:
            records.append(
                CandidateSelectionRecord(
                    candidate_id=candidate.candidate_id,
                    candidate_hash=candidate.candidate_hash,
                    structural_admitted=True,
                    task168_chain_status="CHAIN_COMPLETE",
                    task168_blocked_stage=None,
                    task168_blocked_codes=(),
                    task174_status="BLOCKED",
                    rating_request_ready=False,
                    rating_request_hash=None,
                    task171_result_hash=topology.result_hash,
                    task174_result_hash=getattr(t174, "result_hash", None),
                    selected_for_rating=False,
                )
            )
            continue

        rating_request = _candidate_rating_request(
            candidate, space_hash, bundle, topology, t174, digest
        )
        rating_hash = candidate_rating_request_hash(rating_request)
        pick = selected_id is None
        if pick:
            selected_id = candidate.candidate_id
            selected_rating_hash = rating_hash
            selection_reason = "FIRST_STRUCTURAL_AND_TASK174_READY_UNDER_MVP_POLICY"
        records.append(
            CandidateSelectionRecord(
                candidate_id=candidate.candidate_id,
                candidate_hash=candidate.candidate_hash,
                structural_admitted=True,
                task168_chain_status="CHAIN_COMPLETE",
                task168_blocked_stage=None,
                task168_blocked_codes=(),
                task174_status="VALIDATED",
                rating_request_ready=True,
                rating_request_hash=rating_hash,
                task171_result_hash=topology.result_hash,
                task174_result_hash=t174.result_hash,
                selected_for_rating=pick,
            )
        )

    status = "SELECTED" if selected_id is not None else "BLOCKED_NO_RATING_READY_CANDIDATE"
    return CandidateSelectionOutcome(
        status=status,
        candidate_space_hash=space_hash,
        selected_candidate_id=selected_id,
        selected_rating_request_hash=selected_rating_hash,
        records=tuple(records),
        selection_reason=selection_reason,
    )


def selection_to_json(outcome: CandidateSelectionOutcome) -> dict[str, Any]:
    return {
        "schema_version": "hxforge.candidate-selection-result.v1",
        "status": outcome.status,
        "candidate_space_hash": outcome.candidate_space_hash,
        "selected_candidate_id": outcome.selected_candidate_id,
        "selected_rating_request_hash": outcome.selected_rating_request_hash,
        "selection_reason": outcome.selection_reason,
        "records": [
            {
                "candidate_id": row.candidate_id,
                "candidate_hash": row.candidate_hash,
                "structural_admitted": row.structural_admitted,
                "task168_chain_status": row.task168_chain_status,
                "task168_blocked_stage": row.task168_blocked_stage,
                "task168_blocked_codes": list(row.task168_blocked_codes),
                "task174_status": row.task174_status,
                "rating_request_ready": row.rating_request_ready,
                "rating_request_hash": row.rating_request_hash,
                "task171_result_hash": row.task171_result_hash,
                "task174_result_hash": row.task174_result_hash,
                "selected_for_rating": row.selected_for_rating,
            }
            for row in outcome.records
        ],
    }
