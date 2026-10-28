"""R26F: representative-candidate hydraulic path study (demo vs full-path input)."""

# ruff: noqa: E501

from __future__ import annotations

from typing import Any

from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
    CandidateSelectionRecord,
    enumerate_experimental_rating_candidates,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.engineering_hydraulic_dp_breakdown import (
    build_hydraulic_dp_breakdown,
    shell_dp_components_summary,
    tube_dp_components_summary,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_hydraulic_path_geometry import (
    R26D_HISTORICAL_LONG_BASELINE_REFERENCE,
    assess_full_hydraulic_path_input_status,
    candidate_geometry_from_selection_record,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_engineering_rating_core import (
    ENGINEERING_NUMERIC_VALID,
    run_experimental_engineering_rating,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_engineering_rating_live_bridge import (
    build_experimental_engineering_rating_live_package,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_multi_candidate_engineering_sizing import (
    _is_baseline_candidate_b,
    _nominal_experimental_comparison_status,
)
from prototypes.v07_general_rating_sizing_mvp.positive_duty_cell import build_native_cell_context

_TASK_ID = "V07_R26F_ENGINEERING_HYDRAULIC_PATH_COMPLETION"
_SCHEMA = "hxforge.experimental-engineering-hydraulic-path-study.v26f"


def _mesh_thermal_status(mesh: dict[str, Any] | None) -> str:
    if not mesh:
        return "NOT_EVALUATED"
    if mesh.get("FULL_RATING_CONVERGED"):
        return "FULL_RATING_CONVERGED"
    if mesh.get("SINGLE_MESH_NUMERIC_VALID"):
        return "SINGLE_MESH_NUMERIC_VALID"
    return "NOT_CONVERGED"


def _resolve_representative_records(
    records: tuple[CandidateSelectionRecord, ...],
) -> list[CandidateSelectionRecord]:
    chosen: list[CandidateSelectionRecord] = []
    baseline = next((r for r in records if _is_baseline_candidate_b(r) and r.rating_request_ready), None)
    if baseline:
        chosen.append(baseline)
    middle = next(
        (
            r
            for r in records
            if r.rating_request_ready
            and r.tube_length_m == "3.5"
            and r.baffle_spacing_m == "0.7"
            and r.shell_inside_diameter_m == "0.54"
        ),
        None,
    )
    if middle and all(middle.candidate_id != x.candidate_id for x in chosen):
        chosen.append(middle)
    for record in records:
        if not record.rating_request_ready:
            continue
        if any(record.candidate_id == x.candidate_id for x in chosen):
            continue
        if len(chosen) >= 3:
            break
        chosen.append(record)
    return chosen


def _rate_candidate(
    case: EngineeringCase,
    record: CandidateSelectionRecord,
    selection: Any,
) -> dict[str, Any]:
    native = build_native_cell_context(case, selection=selection, candidate_id=record.candidate_id)
    n1_cache: dict[int, Any] = {}
    n1 = run_experimental_engineering_rating(
        case, subdivisions=1, native=native, mesh_result_cache=n1_cache
    )
    package = None
    if n1.status == ENGINEERING_NUMERIC_VALID:
        package = build_experimental_engineering_rating_live_package(
            case,
            native=native,
            run_mesh_ladder=True,
            run_hydraulic_sensitivity=True,
            mesh_result_cache=n1_cache,
        )
    postpass = (package or {}).get("live_thermal_state_hydraulic_postpass") or {}
    breakdown = build_hydraulic_dp_breakdown(postpass, case=case)
    nominal_ok, nominal_status, nominal_reasons = _nominal_experimental_comparison_status(
        package, case=case
    )
    mesh = (package or {}).get("mesh_convergence") or {}
    margin = (package or {}).get("hydraulic_margin") or {}
    return {
        "candidate_geometry_authority": candidate_geometry_from_selection_record(record),
        "demonstration_entrance_only_model": {
            "THERMAL_NUMERIC_STATUS": (package or {}).get("engineering_delivery_receipt", {}).get(
                "THERMAL_NUMERIC_STATUS"
            ),
            "MESH_CONVERGENCE_STATUS": _mesh_thermal_status(mesh),
            "HYDRAULIC_NOMINAL_STATUS": margin.get("HYDRAULIC_NOMINAL_STATUS"),
            "HYDRAULIC_ROBUSTNESS_STATUS": margin.get("HYDRAULIC_ROBUSTNESS_STATUS"),
            "GEOMETRY_COMPLETENESS_STATUS": (package or {}).get("GEOMETRY_COMPLETENESS_STATUS"),
            "ENGINEERING_SIZING_ELIGIBILITY": (package or {}).get("ENGINEERING_SIZING_ELIGIBILITY"),
            "EXPERIMENTAL_NOMINAL_SIZING_COMPARISON_STATUS": nominal_status,
            "EXPERIMENTAL_NOMINAL_SIZING_FEASIBLE": nominal_ok,
            "nominal_infeasibility_reasons": nominal_reasons,
            "hydraulic_dp_breakdown": breakdown,
            "TUBE_DP_COMPONENTS": tube_dp_components_summary(breakdown),
            "SHELL_DP_COMPONENTS": shell_dp_components_summary(breakdown),
        },
        "authorized_full_path_model": {
            "status": "NOT_RUN",
            "reason": (
                "Full-path hydraulic model requires AUTHORIZED_ENGINEERING_INPUT for tube header, "
                "exit, and shell nozzle transitions; see FULL_PATH_INPUT_STATUS."
            ),
        },
        "model_delta": {
            "status": "NOT_COMPUTED",
            "reason": "Authorized full-path inputs not supplied; no delta vs demonstration model.",
        },
    }


def run_experimental_engineering_hydraulic_path_study(
    case: EngineeringCase,
) -> dict[str, Any]:
    selection = enumerate_experimental_rating_candidates(case)
    path_status = assess_full_hydraulic_path_input_status(case)
    representatives = _resolve_representative_records(selection.records)
    candidate_results = [
        _rate_candidate(case, record, selection) for record in representatives
    ]
    return {
        "schema_version": _SCHEMA,
        "TASK_ID": _TASK_ID,
        "historical_reference_geometries": {
            "r26d_long_baseline": R26D_HISTORICAL_LONG_BASELINE_REFERENCE,
        },
        "FULL_PATH_INPUT_STATUS": path_status["FULL_PATH_INPUT_STATUS"],
        "full_path_input_assessment": path_status,
        "representative_candidate_count": len(representatives),
        "representative_candidates": candidate_results,
        "engineering_questions": {
            "tube_side_loss_breakdown": "See TUBE_DP_COMPONENTS per candidate.",
            "shell_side_loss_breakdown": "See SHELL_DP_COMPONENTS; nozzle row may be INPUT_REQUIRED.",
            "feasibility_change_after_full_path": (
                "Not evaluated until authorized geometry is provided."
            ),
        },
        "PRODUCTION_DESIGN_APPROVED": False,
    }
