"""Experimental live-rating workflow (CLI-backed, R9)."""

# ruff: noqa: E501

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
    candidate_space_to_json,
    enumerate_experimental_rating_candidates,
    selection_to_json,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    EngineeringCase,
    load_general_engineering_case_json,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_candidate_eligibility import (
    build_candidate_eligibility,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_constraint_preview import (
    build_experimental_constraint_preview,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_hydraulic_scope import (
    build_hydraulic_model_scope_document,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_live_run_identity import (
    build_experimental_live_rating_run_identity,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_live_scope import (
    check_experimental_live_rating_scope,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_ranking import (
    build_experimental_pareto_result,
    build_experimental_ranking,
    build_offline_duty_scenarios,
)
from prototypes.v07_general_rating_sizing_mvp.low_mesh_result import low_mesh_result_document
from prototypes.v07_general_rating_sizing_mvp.native_thermal_boundary_binding import (
    build_native_thermal_boundary_from_case,
    disclosure_document,
)
from prototypes.v07_general_rating_sizing_mvp.nominal_geometry import nominal_area_for_native
from prototypes.v07_general_rating_sizing_mvp.positive_duty_cell import (
    build_native_cell_context,
    run_mesh_numeric_with_profile,
)
from prototypes.v07_general_rating_sizing_mvp.preflight import enumerate_task168_candidates
from prototypes.v07_general_rating_sizing_mvp.property_provider_identity import (
    build_property_provider_identity,
)
from prototypes.v07_general_rating_sizing_mvp.report import write_engineering_reports
from prototypes.v07_general_rating_sizing_mvp.sizing_request_builder import (
    build_task173_sizing_request,
    sizing_request_identity,
)

_FEASIBLE_SHELL_LEFT_TEMPERATURE_K = 298.5

ExperimentalLiveStatus = Literal[
    "INPUT_OUT_OF_SUPPORTED_SCOPE",
    "BLOCKED_PREFLIGHT",
    "BLOCKED_CANDIDATE_SELECTION",
    "EXPERIMENTAL_COMPLETE",
    "EXPERIMENTAL_BLOCKED",
]


@dataclass(frozen=True)
class ExperimentalLiveRatingOutcome:
    status: ExperimentalLiveStatus
    engineering_case_id: str
    output_dir: Path
    raw_result_path: Path | None
    raw_result_sha256: str | None
    mesh_status: str | None
    total_numerical_seconds: float
    blocker_code: str | None
    cli_success: bool
    numeric_valid_count: int
    blocked_rating_count: int
    selected_for_rating_count: int
    multi_candidate_mode: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "hxforge.experimental-live-workflow-outcome.v2",
            "status": self.status,
            "engineering_case_id": self.engineering_case_id,
            "raw_result_path": str(self.raw_result_path) if self.raw_result_path else None,
            "raw_result_sha256": self.raw_result_sha256,
            "mesh_status": self.mesh_status,
            "total_numerical_seconds": self.total_numerical_seconds,
            "blocker_code": self.blocker_code,
            "cli_success": self.cli_success,
            "numeric_valid_count": self.numeric_valid_count,
            "blocked_rating_count": self.blocked_rating_count,
            "selected_for_rating_count": self.selected_for_rating_count,
            "multi_candidate_mode": self.multi_candidate_mode,
        }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_experimental_live_rating_workflow(
    case: EngineeringCase,
    output_dir: Path,
    *,
    mesh_level: int = 1,
    enable_ephemeral_tp_cache: bool = False,
    cli_objective: str | None = None,
) -> ExperimentalLiveRatingOutcome:
    output_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    scope_code, scope_detail = check_experimental_live_rating_scope(case)
    (output_dir / "GENERAL_ENGINEERING_CASE.json").write_text(
        case.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    if scope_code != "IN_SCOPE":
        raw = {
            "schema_version": "hxforge.experimental-live-raw-result.v1",
            "status": "INPUT_OUT_OF_SUPPORTED_SCOPE",
            "detail": scope_detail,
        }
        raw_path = output_dir / "RAW_RESULT.json"
        raw_path.write_text(json.dumps(raw, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return ExperimentalLiveRatingOutcome(
            status="INPUT_OUT_OF_SUPPORTED_SCOPE",
            engineering_case_id=case.engineering_case_id,
            output_dir=output_dir,
            raw_result_path=raw_path,
            raw_result_sha256=_sha256_file(raw_path),
            mesh_status=None,
            total_numerical_seconds=time.perf_counter() - t0,
            blocker_code=scope_detail,
            cli_success=False,
            numeric_valid_count=0,
            blocked_rating_count=0,
            selected_for_rating_count=0,
            multi_candidate_mode=False,
        )

    provider = CoolPropProvider()
    binding = build_native_thermal_boundary_from_case(case, provider)
    binding_doc = disclosure_document(binding)
    (output_dir / "NATIVE_THERMAL_BOUNDARY.json").write_text(
        json.dumps(binding_doc, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    sizing_request = build_task173_sizing_request(case)
    (output_dir / "TASK173_SIZING_REQUEST_HASH.txt").write_text(
        sizing_request_identity(sizing_request) + "\n", encoding="utf-8"
    )
    preflight = enumerate_task168_candidates(sizing_request)
    (output_dir / "TASK168_PREFLIGHT.json").write_text(
        json.dumps(preflight, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if preflight.get("status") != "VALID":
        return _blocked_outcome(
            case,
            output_dir,
            t0,
            status="BLOCKED_PREFLIGHT",
            stage="TASK168",
            detail=str(preflight.get("blocked_codes")),
        )

    selection = enumerate_experimental_rating_candidates(case)
    (output_dir / "CANDIDATE_SPACE_RESULT.json").write_text(
        json.dumps(candidate_space_to_json(selection), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "CANDIDATE_SELECTION_RESULT.json").write_text(
        json.dumps(selection_to_json(selection), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    hydraulic_scope = build_hydraulic_model_scope_document()
    (output_dir / "HYDRAULIC_MODEL_SCOPE.json").write_text(
        json.dumps(hydraulic_scope, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not selection.selected_candidate_ids:
        return _blocked_outcome(
            case,
            output_dir,
            t0,
            status="BLOCKED_CANDIDATE_SELECTION",
            stage="CANDIDATE_SELECTION",
            detail=selection.status,
        )

    multi = len(selection.selected_candidate_ids) > 1
    budget_s = min(1200.0, float(case.solver_budget.total_budget_s))
    provider_identity = build_property_provider_identity(provider)
    rating_rows: list[dict[str, Any]] = []
    identity_entries: list[dict[str, Any]] = []

    for candidate_id in selection.selected_candidate_ids:
        if time.perf_counter() - t0 >= budget_s:
            rating_rows.append(
                {
                    "candidate_id": candidate_id,
                    "mesh_status": "BUDGET_STOP",
                    "failure_code": "NUMERICAL_BUDGET_EXCEEDED",
                }
            )
            break
        native = build_native_cell_context(case, selection=selection, candidate_id=candidate_id)
        mesh, profile, obs = run_mesh_numeric_with_profile(
            native,
            subdivisions=mesh_level,
            case=case,
            enable_live_thermal_boundary=True,
            enable_ephemeral_tp_cache=enable_ephemeral_tp_cache,
        )
        numeric_valid = mesh.get("status") == "NUMERIC_VALID"
        if numeric_valid and obs is not None:
            mesh = {
                **mesh,
                "tube_outlet_temperature_k": str(obs.tube_outlet_temperature_k),
                "shell_outlet_temperature_k": str(obs.shell_outlet_temperature_k),
            }
        constraint_preview = build_experimental_constraint_preview(case, mesh=mesh, native=native)
        record = next(
            (rec for rec in selection.records if rec.candidate_id == candidate_id),
            None,
        )
        tube_len = record.tube_length_m if record is not None else ""
        nominal_geometry = nominal_area_for_native(case, native, tube_length_m=tube_len)
        bundle_geometry: dict[str, Any] | None = None
        if record is not None and record.shell_inside_diameter_m is not None:
            bundle_geometry = {
                "shell_inside_diameter_m": record.shell_inside_diameter_m,
                "shell_geometry_id": record.shell_geometry_id,
                "physical_tube_count": record.physical_tube_count,
                "task025_total_parallel_flow_area_m2": (
                    record.task025_total_parallel_flow_area_m2 or native.task025_parallel_area_m2
                ),
            }
        row: dict[str, Any] = {
            "candidate_id": native.candidate_id,
            "candidate_hash": native.candidate_hash,
            "rating_request_hash": native.rating_request_hash,
            "task171_result_hash": native.task171_result_hash,
            "task174_result_hash": native.task174_result_hash,
            "task025_parallel_area_m2": native.task025_parallel_area_m2,
            "bundle_geometry": bundle_geometry,
            "status": mesh.get("status"),
            "mesh_status": mesh.get("status"),
            "nominal_geometry": nominal_geometry,
            "mesh_result_hash": mesh.get("mesh_result_hash"),
            "total_duty_w": mesh.get("total_duty_w"),
            "tube_outlet_temperature_k": mesh.get("tube_outlet_temperature_k"),
            "shell_outlet_temperature_k": mesh.get("shell_outlet_temperature_k"),
            "energy_balance_residual_w": mesh.get("energy_balance_residual_w"),
            "terminal_boundary_residual_k": mesh.get("terminal_boundary_residual_k"),
            "task172_local_evaluation_count": mesh.get("task172_local_evaluation_count"),
            "wall_seconds": mesh.get("wall_seconds"),
            "failure_code": mesh.get("failure_code"),
            "constraint_preview": constraint_preview,
            "solver_performance_profile": profile,
        }
        rating_rows.append(row)
        identity_entries.append(
            {
                "candidate_id": native.candidate_id,
                "rating_request_hash": native.rating_request_hash,
                "mesh_result_hash": mesh.get("mesh_result_hash"),
            }
        )

    (output_dir / "CANDIDATE_RATING_RESULTS.json").write_text(
        json.dumps(
            {
                "schema_version": "hxforge.candidate-rating-results.v1",
                "mesh_level": mesh_level,
                "candidates": rating_rows,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    primary_native = build_native_cell_context(
        case,
        selection=selection,
        candidate_id=selection.selected_candidate_ids[0],
    )
    run_identity = build_experimental_live_rating_run_identity(
        case=case,
        native_candidate_id=primary_native.candidate_id,
        native_candidate_hash=primary_native.candidate_hash,
        rating_request_hash=primary_native.rating_request_hash,
        task171_result_hash=primary_native.task171_result_hash,
        task174_result_hash=primary_native.task174_result_hash,
        task025_parallel_area_m2=primary_native.task025_parallel_area_m2,
        thermal_boundary_binding_doc=binding_doc,
        mesh_level=mesh_level,
        enable_ephemeral_tp_cache=enable_ephemeral_tp_cache,
        provider=provider,
        candidate_rating_entries=tuple(identity_entries),
    )
    run_identity["property_provider_identity"] = provider_identity
    (output_dir / "EXPERIMENTAL_LIVE_RATING_RUN_IDENTITY.json").write_text(
        json.dumps(run_identity, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    eligibility = build_candidate_eligibility(case, selection, rating_rows)
    (output_dir / "EXPERIMENTAL_CANDIDATE_ELIGIBILITY.json").write_text(
        json.dumps(
            {
                "schema_version": "hxforge.experimental-candidate-eligibility.v1",
                "candidates": eligibility,
                "HYDRAULIC_MODEL_SCOPE": "HYDRAULIC_REFERENCE_MODEL_PREVIEW",
                "production_qualification": "PRODUCTION_NOT_QUALIFIED",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    area_comparison = {
        "schema_version": "hxforge.nominal-geometry-area-comparison.v1",
        "candidates": [
            {
                "candidate_id": item["candidate_id"],
                "nominal_geometry": item.get("nominal_geometry"),
            }
            for item in eligibility
        ],
    }
    (output_dir / "NOMINAL_GEOMETRY_AREA_COMPARISON.json").write_text(
        json.dumps(area_comparison, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    ranking = build_experimental_ranking(
        case,
        rating_rows,
        selection=selection,
        cli_objective=cli_objective,
    )
    feasible_ids = ranking.get("feasible_candidate_ids") or []
    pareto = build_experimental_pareto_result(rating_rows, feasible_ids=feasible_ids)
    (output_dir / "EXPERIMENTAL_PARETO_RESULT.json").write_text(
        json.dumps(pareto, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "EXPERIMENTAL_MULTI_CANDIDATE_COMPARISON.json").write_text(
        json.dumps(
            {
                "schema_version": "hxforge.experimental-multi-candidate-comparison.v1",
                "candidates": rating_rows,
                "hydraulic_model_scope": hydraulic_scope["task174_hydraulic_status"],
                "EXPERIMENTAL_COMPARISON_STATUS": ranking["EXPERIMENTAL_COMPARISON_STATUS"],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    if ranking["EXPERIMENTAL_RANKING_STATUS"] in {
        "EXPERIMENTAL_RANKING_AVAILABLE",
        "COMPARISON_ONLY",
    }:
        (output_dir / "EXPERIMENTAL_RANKING_RESULT.json").write_text(
            json.dumps(ranking, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    numeric_valid_count = sum(1 for row in rating_rows if row.get("mesh_status") == "NUMERIC_VALID")
    blocked_count = sum(
        1 for row in rating_rows if row.get("mesh_status") not in {"NUMERIC_VALID", "BUDGET_STOP"}
    )
    selected_count = len(selection.selected_candidate_ids)
    all_selected_valid = numeric_valid_count == selected_count and selected_count > 0

    first_row = rating_rows[0]
    first_mesh_doc = low_mesh_result_document(first_row, mesh_level=mesh_level)
    if first_row.get("mesh_status") == "NUMERIC_VALID":
        (output_dir / "REAL_N1_MESH_RESULT.json").write_text(
            json.dumps(first_mesh_doc, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (output_dir / "EXPERIMENTAL_CONSTRAINT_PREVIEW.json").write_text(
            json.dumps(first_row["constraint_preview"], indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    else:
        (output_dir / "REAL_N1_BLOCKED_RESULT.json").write_text(
            json.dumps(first_mesh_doc, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    scenarios = build_offline_duty_scenarios(
        case,
        rating_rows,
        scenario_targets_w=(
            Decimal("9500"),
            Decimal("38000"),
            Decimal("38500"),
        ),
        objective=ranking.get("experimental_sizing_objective", "PARETO_ONLY"),
    )
    (output_dir / "SIZING_OBJECTIVE_SCENARIOS.json").write_text(
        json.dumps(scenarios, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "R10_CI_COMPATIBILITY_FIX.json").write_text(
        json.dumps(
            {
                "schema_version": "hxforge.r10-ci-compatibility-fix.v1",
                "low_mesh_result_contract": "hxforge.low-mesh-result.v1",
                "status_field_source": "solver_mesh_status",
                "mesh_status_compat_field": True,
                "MESH_RESULT_STATUS_SCHEMA_FIXED": True,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    experimental_mesh: dict[str, Any] = {
        "mode": "experimental-live-rating",
        "mesh_level": mesh_level,
        "multi_candidate": multi,
        "candidate_rating_results": rating_rows,
        "ranking": ranking,
        "candidate_eligibility": eligibility,
        "pareto_result": pareto,
        "sizing_objective_scenarios": scenarios,
        "hydraulic_model_scope": hydraulic_scope,
        "solver_boundary": {
            "thermal_binding": binding_doc,
            "feasible_shell_left_face_temperature_k": _FEASIBLE_SHELL_LEFT_TEMPERATURE_K,
            "live_thermal_boundary_enabled": True,
        },
        "run_identity_hash": run_identity["EXPERIMENTAL_LIVE_RATING_RUN_HASH"],
        "property_provider_identity": provider_identity,
        "full_rating_converged": False,
        "low_mesh_numeric_valid": all_selected_valid,
        "mesh_levels": [row for row in rating_rows if row.get("mesh_status") == "NUMERIC_VALID"],
        "ephemeral_tp_cache_enabled": enable_ephemeral_tp_cache,
    }

    workflow_status = "PARTIAL_RATING_ACCEPTED" if all_selected_valid else "PARTIAL_RATING_BLOCKED"
    report_paths = write_engineering_reports(
        case,
        preflight=preflight,
        sizing_outcome=None,
        output_dir=output_dir,
        workflow_status=workflow_status,
        experimental_mesh=experimental_mesh,
    )

    total_seconds = round(time.perf_counter() - t0, 3)
    selection_mode = getattr(case, "experimental_candidate_selection_mode", "")
    if selection_mode == "VARIABLE_SHELL_BUNDLE_MIN_NOMINAL_AREA_R13":
        task_id = "V07_GENERAL_VARIABLE_BUNDLE_GEOMETRY_SIZING_R13"
    elif selection_mode == "MIN_NOMINAL_TUBE_AREA_SEARCH":
        task_id = "V07_GENERAL_TARGET_DIRECTED_LIVE_SIZING_R12"
    elif multi:
        task_id = "V07_GENERAL_MULTI_CANDIDATE_LIVE_RATING_R10"
    else:
        task_id = "V07_GENERAL_LIVE_RATING_CLI_AND_ENGINEERING_PREVIEW_R9"
    raw: dict[str, Any] = {
        "schema_version": "hxforge.experimental-live-raw-result.v2",
        "task_id": task_id,
        "EXPERIMENTAL_LIVE_RATING_RUN_HASH": run_identity["EXPERIMENTAL_LIVE_RATING_RUN_HASH"],
        "engineering_case_id": case.engineering_case_id,
        "candidate_rating_results": rating_rows,
        "ranking": ranking,
        "property_provider_identity": provider_identity,
        "mesh_level": mesh_level,
        "numeric_valid_count": numeric_valid_count,
        "total_numerical_seconds": total_seconds,
        "report_json_path": str(report_paths[0]),
        "report_md_path": str(report_paths[1]),
    }
    raw_path = output_dir / "RAW_RESULT.json"
    raw_path.write_text(json.dumps(raw, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    raw_sha = _sha256_file(raw_path)

    manifest_names = (
        "GENERAL_ENGINEERING_CASE.json",
        "CANDIDATE_SPACE_RESULT.json",
        "EXPERIMENTAL_LIVE_RATING_RUN_IDENTITY.json",
        "CANDIDATE_SELECTION_RESULT.json",
        "CANDIDATE_RATING_RESULTS.json",
        "EXPERIMENTAL_MULTI_CANDIDATE_COMPARISON.json",
        "EXPERIMENTAL_RANKING_RESULT.json",
        "EXPERIMENTAL_CANDIDATE_ELIGIBILITY.json",
        "EXPERIMENTAL_PARETO_RESULT.json",
        "NOMINAL_GEOMETRY_AREA_COMPARISON.json",
        "SIZING_OBJECTIVE_SCENARIOS.json",
        "R10_CI_COMPATIBILITY_FIX.json",
        "HYDRAULIC_MODEL_SCOPE.json",
        "NATIVE_THERMAL_BOUNDARY.json",
        "REAL_N1_MESH_RESULT.json",
        "REAL_N1_BLOCKED_RESULT.json",
        "EXPERIMENTAL_CONSTRAINT_PREVIEW.json",
        "ENGINEERING_REPORT.json",
        "ENGINEERING_REPORT.md",
        "RAW_RESULT.json",
    )
    manifest_entries = {
        name: _sha256_file(output_dir / name)
        for name in manifest_names
        if (output_dir / name).is_file()
    }

    (output_dir / "EVIDENCE_MANIFEST.json").write_text(
        json.dumps(
            {
                "schema_version": "hxforge.evidence-manifest.v1",
                "task_id": task_id,
                "files": manifest_entries,
                "EXPERIMENTAL_LIVE_RATING_RUN_HASH": run_identity[
                    "EXPERIMENTAL_LIVE_RATING_RUN_HASH"
                ],
                "total_numerical_seconds": total_seconds,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    primary_status = str(first_row.get("mesh_status"))
    return ExperimentalLiveRatingOutcome(
        status="EXPERIMENTAL_COMPLETE" if all_selected_valid else "EXPERIMENTAL_BLOCKED",
        engineering_case_id=case.engineering_case_id,
        output_dir=output_dir,
        raw_result_path=raw_path,
        raw_result_sha256=raw_sha,
        mesh_status=primary_status,
        total_numerical_seconds=total_seconds,
        blocker_code=first_row.get("failure_code") if not all_selected_valid else None,
        cli_success=all_selected_valid,
        numeric_valid_count=numeric_valid_count,
        blocked_rating_count=blocked_count,
        selected_for_rating_count=selected_count,
        multi_candidate_mode=multi,
    )


def _blocked_outcome(
    case: EngineeringCase,
    output_dir: Path,
    t0: float,
    *,
    status: ExperimentalLiveStatus,
    stage: str,
    detail: str | None,
) -> ExperimentalLiveRatingOutcome:
    raw = {
        "schema_version": "hxforge.experimental-live-raw-result.v1",
        "status": status,
        "stage": stage,
        "detail": detail,
    }
    raw_path = output_dir / "RAW_RESULT.json"
    raw_path.write_text(json.dumps(raw, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return ExperimentalLiveRatingOutcome(
        status=status,
        engineering_case_id=case.engineering_case_id,
        output_dir=output_dir,
        raw_result_path=raw_path,
        raw_result_sha256=_sha256_file(raw_path),
        mesh_status=None,
        total_numerical_seconds=time.perf_counter() - t0,
        blocker_code=detail,
        cli_success=False,
        numeric_valid_count=0,
        blocked_rating_count=0,
        selected_for_rating_count=0,
        multi_candidate_mode=False,
    )


def run_experimental_live_rating_from_paths(
    input_path: Path,
    output_dir: Path,
    *,
    mesh_level: int = 1,
    cli_objective: str | None = None,
) -> ExperimentalLiveRatingOutcome:
    case = load_general_engineering_case_json(input_path.read_text(encoding="utf-8"))
    return run_experimental_live_rating_workflow(
        case,
        output_dir,
        mesh_level=mesh_level,
        enable_ephemeral_tp_cache=False,
        cli_objective=cli_objective,
    )
