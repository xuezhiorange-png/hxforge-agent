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
from prototypes.v07_general_rating_sizing_mvp.candidate_selection_policy import (
    apply_rating_selection_policy,
    nominal_area_proxy_m2,
    resolve_candidate_selection_mode,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.sizing_request_builder import (
    build_task173_sizing_request,
)


@dataclass(frozen=True)
class CandidateSelectionRecord:
    candidate_id: str
    candidate_hash: str
    tube_length_m: str
    baffle_spacing_m: str
    geometry_projection_hash: str
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
    task173_rating_status: str
    physical_tube_count: int | None = None
    nominal_tube_outer_area_proxy_m2: str | None = None


@dataclass(frozen=True)
class CandidateSelectionOutcome:
    status: str
    candidate_space_hash: str
    selected_candidate_id: str | None
    selected_candidate_ids: tuple[str, ...]
    selected_rating_request_hash: str | None
    records: tuple[CandidateSelectionRecord, ...]
    selection_reason: str | None

    @property
    def candidate_space_count(self) -> int:
        return len(self.records)

    @property
    def structurally_admitted_count(self) -> int:
        return sum(1 for row in self.records if row.structural_admitted)

    @property
    def task174_ready_count(self) -> int:
        return sum(1 for row in self.records if row.rating_request_ready)

    @property
    def selected_for_rating_count(self) -> int:
        return sum(1 for row in self.records if row.selected_for_rating)


def _geometry_projection_hash(tube_length_m: str, baffle_spacing_m: str) -> str:
    from hexagent.canonical_json import canonical_sha256

    return canonical_sha256(
        {
            "tube_length_m": tube_length_m,
            "baffle_spacing_m": baffle_spacing_m,
        }
    )


def enumerate_experimental_rating_candidates(case: EngineeringCase) -> CandidateSelectionOutcome:
    """Enumerate full discrete space; select up to max_candidates_to_rate for mesh rating."""
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
    max_rate = case.solver_budget.max_candidates_to_rate
    from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
        candidate_rating_request_hash,
    )

    records: list[CandidateSelectionRecord] = []
    selection_mode = resolve_candidate_selection_mode(case)
    defer_selection = selection_mode == "MIN_NOMINAL_TUBE_AREA_SEARCH"
    selected_ids: list[str] = []
    selected_rating_hash: str | None = None
    selection_reason: str | None = None
    selected_geometry: set[str] = set()

    for combination in itertools.product(t168.shell_geometry_catalog.records, *dimensions):
        candidate = task168._candidate(t168, authorities, combination[0], tuple(combination[1:]))
        tube_len = str(candidate.tube_length_m)
        baffle_space = str(candidate.baffle_spacing_m)
        geom_hash = _geometry_projection_hash(tube_len, baffle_space)
        structural_blockers = task168._structural_blockers(candidate)
        if structural_blockers:
            blocker_codes = tuple(str(item.code) for item in structural_blockers)
            records.append(
                CandidateSelectionRecord(
                    candidate_id=candidate.candidate_id,
                    candidate_hash=candidate.candidate_hash,
                    tube_length_m=tube_len,
                    baffle_spacing_m=baffle_space,
                    geometry_projection_hash=geom_hash,
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
                    task173_rating_status="NOT_RUN",
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
                    tube_length_m=tube_len,
                    baffle_spacing_m=baffle_space,
                    geometry_projection_hash=geom_hash,
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
                    task173_rating_status="NOT_RUN",
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
                    tube_length_m=tube_len,
                    baffle_spacing_m=baffle_space,
                    geometry_projection_hash=geom_hash,
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
                    task173_rating_status="NOT_RUN",
                )
            )
            continue

        rating_request = _candidate_rating_request(
            candidate, space_hash, bundle, topology, t174, digest
        )
        rating_hash = candidate_rating_request_hash(rating_request)
        physical_tube_count = bundle.task021_layout.physical_tube_count
        nominal_area = nominal_area_proxy_m2(
            case,
            tube_length_m=tube_len,
            physical_tube_count=physical_tube_count,
        )
        pick = False
        if not defer_selection:
            pick = len(selected_ids) < max_rate and geom_hash not in selected_geometry
            if pick:
                selected_ids.append(candidate.candidate_id)
                selected_geometry.add(geom_hash)
                if selected_rating_hash is None:
                    selected_rating_hash = rating_hash
                if selection_reason is None:
                    selection_reason = (
                        "FIRST_N_DISTINCT_GEOMETRY_TASK174_READY_UNDER_SOLVER_BUDGET"
                    )
        records.append(
            CandidateSelectionRecord(
                candidate_id=candidate.candidate_id,
                candidate_hash=candidate.candidate_hash,
                tube_length_m=tube_len,
                baffle_spacing_m=baffle_space,
                geometry_projection_hash=geom_hash,
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
                task173_rating_status="SELECTED" if pick else "NOT_SELECTED",
                physical_tube_count=physical_tube_count,
                nominal_tube_outer_area_proxy_m2=nominal_area,
            )
        )

    if defer_selection:
        selected_tuple, selection_reason = apply_rating_selection_policy(case, records)
        if selected_tuple:
            first = next(r for r in records if r.candidate_id == selected_tuple[0])
            selected_rating_hash = first.rating_request_hash
    else:
        selected_tuple = tuple(selected_ids)
    status = "SELECTED" if selected_tuple else "BLOCKED_NO_RATING_READY_CANDIDATE"
    return CandidateSelectionOutcome(
        status=status,
        candidate_space_hash=space_hash,
        selected_candidate_id=selected_tuple[0] if selected_tuple else None,
        selected_candidate_ids=selected_tuple,
        selected_rating_request_hash=selected_rating_hash,
        records=tuple(records),
        selection_reason=selection_reason,
    )


def candidate_space_to_json(outcome: CandidateSelectionOutcome) -> dict[str, Any]:
    distinct_geometry = len({row.geometry_projection_hash for row in outcome.records})
    return {
        "schema_version": "hxforge.candidate-space-result.v1",
        "candidate_space_hash": outcome.candidate_space_hash,
        "candidate_space_count": outcome.candidate_space_count,
        "structurally_admitted_count": outcome.structurally_admitted_count,
        "task174_ready_count": outcome.task174_ready_count,
        "selected_for_rating_count": outcome.selected_for_rating_count,
        "distinct_geometry_count": distinct_geometry,
        "max_candidates_to_rate": "from_case_solver_budget",
        "records": [
            {
                "candidate_id": row.candidate_id,
                "candidate_hash": row.candidate_hash,
                "tube_length_m": row.tube_length_m,
                "baffle_spacing_m": row.baffle_spacing_m,
                "geometry_projection_hash": row.geometry_projection_hash,
                "structural_admitted": row.structural_admitted,
                "task168_chain_status": row.task168_chain_status,
                "task174_status": row.task174_status,
                "rating_request_ready": row.rating_request_ready,
                "nominal_tube_outer_area_proxy_m2": row.nominal_tube_outer_area_proxy_m2,
                "physical_tube_count": row.physical_tube_count,
            }
            for row in outcome.records
        ],
    }


def selection_to_json(outcome: CandidateSelectionOutcome) -> dict[str, Any]:
    return {
        "schema_version": "hxforge.candidate-selection-result.v2",
        "status": outcome.status,
        "candidate_space_hash": outcome.candidate_space_hash,
        "selected_candidate_id": outcome.selected_candidate_id,
        "selected_candidate_ids": list(outcome.selected_candidate_ids),
        "selected_rating_request_hash": outcome.selected_rating_request_hash,
        "selection_reason": outcome.selection_reason,
        "candidate_space_count": outcome.candidate_space_count,
        "structurally_admitted_count": outcome.structurally_admitted_count,
        "task174_ready_count": outcome.task174_ready_count,
        "selected_for_rating_count": outcome.selected_for_rating_count,
        "records": [
            {
                "candidate_id": row.candidate_id,
                "candidate_hash": row.candidate_hash,
                "tube_length_m": row.tube_length_m,
                "baffle_spacing_m": row.baffle_spacing_m,
                "geometry_projection_hash": row.geometry_projection_hash,
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
                "task173_rating_status": row.task173_rating_status,
                "nominal_tube_outer_area_proxy_m2": row.nominal_tube_outer_area_proxy_m2,
                "physical_tube_count": row.physical_tube_count,
            }
            for row in outcome.records
        ],
    }
