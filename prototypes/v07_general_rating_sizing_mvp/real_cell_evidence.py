"""Capture a validated Task172 cell evaluation for evidence (P0)."""

from __future__ import annotations

import itertools
import json
from pathlib import Path
from typing import Any, cast

from hexagent.exchangers.shell_tube.bell_delaware.models import Task166BlockedResult, Task166Result
from hexagent.exchangers.shell_tube.manufacturable_candidates import service as task168
from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import candidate_space_hash
from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
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
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_general_rating_sizing_mvp.engineering_input import GeneralEngineeringCaseV1
from prototypes.v07_general_rating_sizing_mvp.sizing_request_builder import (
    build_task173_sizing_request,
)


def capture_validated_zero_duty_cell(case: GeneralEngineeringCaseV1) -> dict[str, Any]:
    sizing_req = build_task173_sizing_request(case)
    t168 = sizing_req.task168_candidate_request
    authorities = task168._authority_map(t168)
    dimensions = tuple(
        task168._sort_values(authorities[role].values)
        for role in DIMENSION_ORDER
        if role != "SHELL_GEOMETRY_ID"
    )
    provider = CoolPropProvider()
    for combination in itertools.product(t168.shell_geometry_catalog.records, *dimensions):
        candidate = task168._candidate(t168, authorities, combination[0], tuple(combination[1:]))
        if task168._structural_blockers(candidate):
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
            continue
        rr = _candidate_rating_request(
            candidate,
            candidate_space_hash(t168, t168.discrete_candidate_set_authorities),
            bundle,
            topology,
            t174,
            sizing_req.requirement_authority.canonical_hash,
        )
        ctx = t173._candidate_context(rr)
        token = t173._CANDIDATE_RATING_CONTEXT.set(ctx)
        try:
            support = t173._build_candidate_local_support(ctx, 0, 1, 0)
            tube = t173._state_at_inlet(provider, t173.TUBE_INLET_T_K)
            shell = t173._state_at_inlet(provider, t173.SHELL_INLET_T_K)
            evaluation = t173._cell_evaluation(
                0.0,
                support=support,
                tube_upstream=tube,
                shell_physical_left=shell,
                provider=provider,
                shell_authority=ctx.shell_authority,
            )
            task172 = evaluation.task172_result
            return {
                "schema_version": "hxforge.real-task172-cell-result.v1",
                "status": "VALIDATED",
                "candidate_id": candidate.candidate_id,
                "candidate_hash": candidate.candidate_hash,
                "task171_result_hash": topology.result_hash,
                "task174_result_hash": t174.result_hash,
                "task025_total_parallel_flow_area_m2": str(
                    bundle.task025_result.total_parallel_flow_area_m2
                ),
                "physical_tube_count": bundle.task021_layout.physical_tube_count,
                "trial_heat_rate_w": "0",
                "task172_result_hash": task172.result_hash,
                "task172_request_hash": task172.request_hash,
                "task172_status": task172.status,
                "signed_q_hot_to_cold_w": str(task172.signed_q_hot_to_cold_w),
                "mesh_subdivisions": 1,
                "cell_index": 0,
                "notes": (
                    "Exact-zero-duty cell uses Task173 zero-q state portability authority; "
                    "constitutive closure is native Task172 VALIDATED."
                ),
            }
        finally:
            t173._CANDIDATE_RATING_CONTEXT.reset(token)
    raise RuntimeError("no candidate produced a validated Task172 cell")


def write_real_cell_result(case: GeneralEngineeringCaseV1, path: Path) -> dict[str, Any]:
    payload = capture_validated_zero_duty_cell(case)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload
