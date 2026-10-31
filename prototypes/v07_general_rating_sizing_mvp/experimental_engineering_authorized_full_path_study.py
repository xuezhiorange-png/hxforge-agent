"""R26G authorized full-path hydraulic study entry point."""

# ruff: noqa: E501

from __future__ import annotations

from pathlib import Path
from typing import Any

from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
    enumerate_experimental_rating_candidates,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.engineering_hydraulic_path_input_v1 import (
    EngineeringHydraulicPathInputV1,
    build_r26g_demonstration_hydraulic_path_input_v1,
    load_engineering_hydraulic_path_input_v1_json,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_engineering_hydraulic_path_study import (
    run_experimental_engineering_hydraulic_path_study,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_multi_candidate_engineering_sizing import (
    _is_baseline_candidate_b,
)

_TASK_ID = "V07_R26G_AUTHORIZED_FULL_PATH_HYDRAULIC_CALCULATION"
_TASK_ID_A = "V07_R26G_A_FULL_PATH_PHYSICAL_CONSISTENCY_GATE"
_SCHEMA = "hxforge.experimental-engineering-authorized-full-path-study.v26g"


def _representative_ids(case: EngineeringCase) -> list[str]:
    selection = enumerate_experimental_rating_candidates(case)
    ids: list[str] = []
    baseline = next(
        (r for r in selection.records if _is_baseline_candidate_b(r) and r.rating_request_ready),
        None,
    )
    if baseline:
        ids.append(baseline.candidate_id)
    middle = next(
        (
            r
            for r in selection.records
            if r.rating_request_ready
            and r.tube_length_m == "3.5"
            and r.baffle_spacing_m == "0.7"
            and r.shell_inside_diameter_m == "0.54"
        ),
        None,
    )
    if middle and middle.candidate_id not in ids:
        ids.append(middle.candidate_id)
    return ids


def load_hydraulic_path_inputs_from_json_files(
    paths: list[str | Path],
) -> dict[str, EngineeringHydraulicPathInputV1]:
    path_map: dict[str, EngineeringHydraulicPathInputV1] = {}
    for raw_path in paths:
        text = Path(raw_path).read_text(encoding="utf-8")
        path_input = load_engineering_hydraulic_path_input_v1_json(text)
        path_map[path_input.binding.candidate_id] = path_input
    return path_map


def run_r26g_authorized_full_path_hydraulic_study(
    case: EngineeringCase,
    *,
    use_demonstration_path_inputs: bool = False,
    hydraulic_path_inputs: dict[str, EngineeringHydraulicPathInputV1] | None = None,
    task_id: str | None = None,
) -> dict[str, Any]:
    path_map: dict[str, EngineeringHydraulicPathInputV1] = dict(hydraulic_path_inputs or {})
    if use_demonstration_path_inputs:
        selection = enumerate_experimental_rating_candidates(case)
        records_by_id = {r.candidate_id: r for r in selection.records}
        for candidate_id in _representative_ids(case):
            record = records_by_id[candidate_id]
            path_map[candidate_id] = build_r26g_demonstration_hydraulic_path_input_v1(
                case=case, record=record
            )
    report = run_experimental_engineering_hydraulic_path_study(
        case,
        hydraulic_path_inputs=path_map or None,
        task_id=task_id or _TASK_ID_A,
    )
    report["schema_version"] = _SCHEMA
    report["ENGINEERING_SIZING_ELIGIBILITY"] = "DEMONSTRATION_ONLY_NOT_ENGINEERING_SIZING_ELIGIBLE"
    report["PRODUCTION_DESIGN_APPROVED"] = False
    return report
