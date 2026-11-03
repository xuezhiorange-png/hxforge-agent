"""End-to-end general engineering workflow orchestration."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from hexagent.exchangers.shell_tube.task173_integrated_sizing import (
    Task173SizingBlockedResult,
    Task173SizingSuccessResult,
    validate_sizing_request,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.input_to_solver_binding import (
    write_input_to_solver_binding,
)
from prototypes.v07_general_rating_sizing_mvp.native_binding_diagnostics import (
    EVALUATION_AUTHORITY_ORIENTATION_FIX,
    write_native_binding_diagnostics,
)
from prototypes.v07_general_rating_sizing_mvp.preflight import enumerate_task168_candidates
from prototypes.v07_general_rating_sizing_mvp.report import write_engineering_reports
from prototypes.v07_general_rating_sizing_mvp.sizing_request_builder import (
    build_task173_sizing_request,
    sizing_request_identity,
)

WorkflowStatus = Literal[
    "BLOCKED_INPUT",
    "BLOCKED_PREFLIGHT",
    "BLOCKED_SIZING",
    "PREFLIGHT_COMPLETE",
    "PARTIAL_RATING_BUDGET",
    "PARTIAL_RATING_BLOCKED",
    "PARTIAL_RATING_ACCEPTED",
    "SIZING_EVALUATED",
    "EXPERIMENTAL_COMPLETE",
]


@dataclass(frozen=True)
class GeneralWorkflowOutcome:
    status: WorkflowStatus
    engineering_case_id: str
    experimental_ranking_status: str
    production_design_approved: bool
    preflight: dict[str, Any]
    sizing_outcome_type: str
    sizing_result: dict[str, Any] | None
    total_wall_seconds: float
    rating_solver_calls: int
    report_json_path: Path | None
    report_md_path: Path | None
    diagnostics: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "hxforge.general-workflow-outcome.v1",
            "status": self.status,
            "engineering_case_id": self.engineering_case_id,
            "experimental_ranking_status": self.experimental_ranking_status,
            "production_design_approved": self.production_design_approved,
            "preflight": self.preflight,
            "sizing_outcome_type": self.sizing_outcome_type,
            "sizing_result": self.sizing_result,
            "total_wall_seconds": self.total_wall_seconds,
            "rating_solver_calls": self.rating_solver_calls,
            "report_json_path": str(self.report_json_path) if self.report_json_path else None,
            "report_md_path": str(self.report_md_path) if self.report_md_path else None,
            "diagnostics": list(self.diagnostics),
        }


def _serialize_sizing_outcome(
    outcome: Task173SizingSuccessResult | Task173SizingBlockedResult,
) -> dict[str, Any]:
    return json.loads(outcome.model_dump_json())


def run_general_engineering_workflow(
    case: EngineeringCase,
    output_dir: Path,
    *,
    run_full_rating: bool = True,
) -> GeneralWorkflowOutcome:
    output_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    scope, detail = case.applicability_status()
    if scope == "BLOCKED":
        return GeneralWorkflowOutcome(
            status="BLOCKED_INPUT",
            engineering_case_id=case.engineering_case_id,
            experimental_ranking_status="NOT_RUN",
            production_design_approved=False,
            preflight={},
            sizing_outcome_type="NONE",
            sizing_result=None,
            total_wall_seconds=time.perf_counter() - t0,
            rating_solver_calls=0,
            report_json_path=None,
            report_md_path=None,
            diagnostics=(detail or "input_blocked",),
        )

    write_native_binding_diagnostics(output_dir, (EVALUATION_AUTHORITY_ORIENTATION_FIX,))
    write_input_to_solver_binding(case, output_dir / "INPUT_TO_SOLVER_BINDING.json")

    sizing_request = build_task173_sizing_request(case)
    (output_dir / "TASK173_SIZING_REQUEST_HASH.txt").write_text(
        sizing_request_identity(sizing_request) + "\n", encoding="utf-8"
    )
    (output_dir / "GENERAL_ENGINEERING_CASE.json").write_text(
        case.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )

    preflight = enumerate_task168_candidates(sizing_request)
    (output_dir / "TASK168_PREFLIGHT.json").write_text(
        json.dumps(preflight, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if preflight.get("status") != "VALID":
        return GeneralWorkflowOutcome(
            status="BLOCKED_PREFLIGHT",
            engineering_case_id=case.engineering_case_id,
            experimental_ranking_status="NOT_RUN",
            production_design_approved=False,
            preflight=preflight,
            sizing_outcome_type="NONE",
            sizing_result=None,
            total_wall_seconds=time.perf_counter() - t0,
            rating_solver_calls=0,
            report_json_path=None,
            report_md_path=None,
            diagnostics=tuple(preflight.get("blocked_codes", ())),
        )

    if not run_full_rating or not case.solver_budget.enable_full_task173_rating:
        report_paths = write_engineering_reports(
            case,
            preflight=preflight,
            sizing_outcome=None,
            output_dir=output_dir,
            workflow_status="PREFLIGHT_COMPLETE",
        )
        return GeneralWorkflowOutcome(
            status="PREFLIGHT_COMPLETE",
            engineering_case_id=case.engineering_case_id,
            experimental_ranking_status="PREFLIGHT_ONLY",
            production_design_approved=False,
            preflight=preflight,
            sizing_outcome_type="SKIPPED",
            sizing_result=None,
            total_wall_seconds=time.perf_counter() - t0,
            rating_solver_calls=0,
            report_json_path=report_paths[0],
            report_md_path=report_paths[1],
            diagnostics=("full_task173_rating_skipped",),
        )

    outcome = validate_sizing_request(sizing_request)
    serialized = _serialize_sizing_outcome(outcome)
    (output_dir / "TASK173_SIZING_OUTCOME.json").write_text(
        json.dumps(serialized, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    rated = 0
    accepted_mesh = 0
    if isinstance(outcome, Task173SizingSuccessResult):
        rated = sum(1 for row in outcome.candidate_records if row.candidate_rating_request_hash)
        accepted_mesh = sum(
            1
            for row in outcome.candidate_records
            if row.disposition == "EVALUATED" and row.accepted_subdivisions_per_interval is not None
        )

    if isinstance(outcome, Task173SizingBlockedResult):
        wf_status: WorkflowStatus = "BLOCKED_SIZING"
        ranking_status = "BLOCKED"
    elif accepted_mesh == 0:
        wf_status = "PARTIAL_RATING_BLOCKED"
        ranking_status = "EXPERIMENTAL_RANKING_BLOCKED"
    elif outcome.selection_status == "RECOMMENDATION_AVAILABLE":
        wf_status = "SIZING_EVALUATED"
        ranking_status = "EXPERIMENTAL_RANKING_AVAILABLE"
    else:
        wf_status = "PARTIAL_RATING_ACCEPTED"
        ranking_status = "EXPERIMENTAL_RANKING_BLOCKED"

    report_paths = write_engineering_reports(
        case,
        preflight=preflight,
        sizing_outcome=outcome if isinstance(outcome, Task173SizingSuccessResult) else None,
        output_dir=output_dir,
        workflow_status=wf_status,
    )

    return GeneralWorkflowOutcome(
        status=wf_status,
        engineering_case_id=case.engineering_case_id,
        experimental_ranking_status=ranking_status,
        production_design_approved=False,
        preflight=preflight,
        sizing_outcome_type=type(outcome).__name__,
        sizing_result=serialized,
        total_wall_seconds=time.perf_counter() - t0,
        rating_solver_calls=rated,
        report_json_path=report_paths[0],
        report_md_path=report_paths[1],
        diagnostics=(),
    )
