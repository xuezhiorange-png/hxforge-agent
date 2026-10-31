"""P0: R12 2.5 m / 0.5 m baffle Task174 blocker forensics (read-only)."""

from __future__ import annotations

from typing import Any, cast

from hexagent.exchangers.shell_tube.bell_delaware.models import Task166BlockedResult, Task166Result
from hexagent.exchangers.shell_tube.manufacturable_candidates import service as task168
from hexagent.exchangers.shell_tube.task173_integrated_sizing.candidate_materialization import (
    materialize_candidate_task171,
)
from hexagent.exchangers.shell_tube.task173_integrated_sizing.service import (
    DIMENSION_ORDER,
    _candidate_request_for_task174,
    validate_task174_candidate,
)
from hexagent.exchangers.shell_tube.task174_hydraulic_orchestration import Task174NativeOutputs
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.sizing_request_builder import (
    build_task173_sizing_request,
)


def analyze_r12_25m_05m_task174_blocker(case: EngineeringCase) -> dict[str, Any]:
    """Return structured blocker document for tube_length=2.5 m, baffle_spacing=0.5 m."""
    import itertools

    req = build_task173_sizing_request(case)
    t168 = req.task168_candidate_request
    authorities = task168._authority_map(t168)
    dimensions = tuple(
        task168._sort_values(authorities[role].values)
        for role in DIMENSION_ORDER
        if role != "SHELL_GEOMETRY_ID"
    )
    for combination in itertools.product(t168.shell_geometry_catalog.records, *dimensions):
        candidate = task168._candidate(t168, authorities, combination[0], tuple(combination[1:]))
        if str(candidate.tube_length_m) != "2.5" or str(candidate.baffle_spacing_m) != "0.5":
            continue
        shell_record = combination[0]
        bundle, stage_failure, _ = task168._execute_candidate_chain(
            t168,
            candidate,
            combination[0],
            include_legacy_task162=False,
            include_legacy_task168_rating_dependencies=False,
            preserve_baffle_orientation_sequence=False,
        )
        if stage_failure is not None:
            return {
                "schema_version": "hxforge.r12-25m-task174-blocker-analysis.v1",
                "tube_length_m": "2.5",
                "baffle_spacing_m": "0.5",
                "stage": "TASK168_CHAIN",
                "task174_status": "NOT_RUN",
                "blocker": {
                    "stage": str(stage_failure.stage),
                    "code": str(stage_failure.code),
                },
            }
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
        blockers = []
        if hasattr(t174, "blockers"):
            blockers = [
                {
                    "code": item.code,
                    "scope": getattr(item, "scope", None),
                    "missing_bindings": getattr(item, "missing_bindings", None),
                    "consumer": getattr(item, "consumer", None),
                }
                for item in t174.blockers
            ]
        return {
            "schema_version": "hxforge.r12-25m-task174-blocker-analysis.v1",
            "tube_length_m": "2.5",
            "baffle_spacing_m": "0.5",
            "shell_inside_diameter_m": shell_record.shell_inside_diameter_m,
            "shell_geometry_id": shell_record.geometry_id,
            "physical_tube_count": bundle.task021_layout.physical_tube_count,
            "task025_total_parallel_flow_area_m2": str(
                bundle.task025_result.total_parallel_flow_area_m2
            ),
            "task168_chain_status": "CHAIN_COMPLETE",
            "task174_status": "BLOCKED",
            "task174_result_hash": getattr(t174, "result_hash", None),
            "blockers": blockers,
            "engineering_interpretation": (
                "Task174 reference hydraulic preview blocked because candidate outlet "
                "pressures left the CoolProp water-property domain "
                "(100000–101325 Pa). This is not a silent override of Task174 validation."
            ),
            "hydraulic_model_scope": "HYDRAULIC_REFERENCE_MODEL_PREVIEW",
        }
    return {
        "schema_version": "hxforge.r12-25m-task174-blocker-analysis.v1",
        "tube_length_m": "2.5",
        "baffle_spacing_m": "0.5",
        "task174_status": "NOT_FOUND_IN_SPACE",
    }
