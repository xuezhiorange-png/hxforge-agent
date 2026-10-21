"""Experimental live-rating workflow (CLI-backed, R9)."""

# ruff: noqa: E501

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
    enumerate_experimental_rating_candidates,
    selection_to_json,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    EngineeringCase,
    load_general_engineering_case_json,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_constraint_preview import (
    build_experimental_constraint_preview,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_live_run_identity import (
    build_experimental_live_rating_run_identity,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_live_scope import (
    check_experimental_live_rating_scope,
)
from prototypes.v07_general_rating_sizing_mvp.native_thermal_boundary_binding import (
    build_native_thermal_boundary_from_case,
    disclosure_document,
)
from prototypes.v07_general_rating_sizing_mvp.positive_duty_cell import (
    build_native_cell_context,
    run_mesh_numeric_with_profile,
)
from prototypes.v07_general_rating_sizing_mvp.preflight import enumerate_task168_candidates
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "hxforge.experimental-live-workflow-outcome.v1",
            "status": self.status,
            "engineering_case_id": self.engineering_case_id,
            "raw_result_path": str(self.raw_result_path) if self.raw_result_path else None,
            "raw_result_sha256": self.raw_result_sha256,
            "mesh_status": self.mesh_status,
            "total_numerical_seconds": self.total_numerical_seconds,
            "blocker_code": self.blocker_code,
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
    (output_dir / "CANDIDATE_SELECTION_RESULT.json").write_text(
        json.dumps(selection_to_json(selection), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if selection.selected_candidate_id is None:
        return _blocked_outcome(
            case,
            output_dir,
            t0,
            status="BLOCKED_CANDIDATE_SELECTION",
            stage="CANDIDATE_SELECTION",
            detail=selection.status,
        )

    native = build_native_cell_context(case, selection=selection)
    run_identity = build_experimental_live_rating_run_identity(
        case=case,
        native_candidate_id=native.candidate_id,
        native_candidate_hash=native.candidate_hash,
        rating_request_hash=native.rating_request_hash,
        task171_result_hash=native.task171_result_hash,
        task174_result_hash=native.task174_result_hash,
        task025_parallel_area_m2=native.task025_parallel_area_m2,
        thermal_boundary_binding_doc=binding_doc,
        mesh_level=mesh_level,
        enable_ephemeral_tp_cache=enable_ephemeral_tp_cache,
        provider=provider,
    )
    (output_dir / "EXPERIMENTAL_LIVE_RATING_RUN_IDENTITY.json").write_text(
        json.dumps(run_identity, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

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
        result_name = "REAL_N1_MESH_RESULT.json"
    else:
        result_name = "REAL_N1_BLOCKED_RESULT.json"
    (output_dir / result_name).write_text(
        json.dumps(mesh, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    constraint_preview = build_experimental_constraint_preview(case, mesh=mesh, native=native)
    (output_dir / "EXPERIMENTAL_CONSTRAINT_PREVIEW.json").write_text(
        json.dumps(constraint_preview, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    experimental_mesh: dict[str, Any] = {
        "mode": "experimental-live-rating",
        "mesh_level": mesh_level,
        "live_boundary_n1_numeric_valid": numeric_valid,
        "mesh_result": mesh,
        "solver_performance_profile": profile,
        "solver_boundary": {
            "thermal_binding": binding_doc,
            "feasible_shell_left_face_temperature_k": _FEASIBLE_SHELL_LEFT_TEMPERATURE_K,
            "live_thermal_boundary_enabled": True,
        },
        "geometry_summary": {
            "candidate_id": native.candidate_id,
            "candidate_hash": native.candidate_hash,
            "task025_parallel_area_m2": native.task025_parallel_area_m2,
            "physical_tube_count": native.physical_tube_count,
            "task171_result_hash": native.task171_result_hash,
            "task174_result_hash": native.task174_result_hash,
        },
        "constraint_preview": constraint_preview,
        "run_identity_hash": run_identity["EXPERIMENTAL_LIVE_RATING_RUN_HASH"],
        "full_rating_converged": False,
        "low_mesh_numeric_valid": numeric_valid,
        "mesh_levels": [mesh] if numeric_valid else [],
        "property_provider_identity": "CoolPropProvider",
        "ephemeral_tp_cache_enabled": enable_ephemeral_tp_cache,
    }
    if obs is not None:
        experimental_mesh["mesh_observables"] = {
            "total_duty_w": str(obs.total_duty_w),
            "tube_outlet_temperature_k": str(obs.tube_outlet_temperature_k),
            "shell_outlet_temperature_k": str(obs.shell_outlet_temperature_k),
            "energy_balance_residual_w": str(obs.energy_balance_residual_w),
            "terminal_boundary_residual_k": str(obs.terminal_boundary_residual_k),
        }

    workflow_status = "PARTIAL_RATING_ACCEPTED" if numeric_valid else "PARTIAL_RATING_BLOCKED"
    report_paths = write_engineering_reports(
        case,
        preflight=preflight,
        sizing_outcome=None,
        output_dir=output_dir,
        workflow_status=workflow_status,
        experimental_mesh=experimental_mesh,
    )

    total_seconds = round(time.perf_counter() - t0, 3)
    raw: dict[str, Any] = {
        "schema_version": "hxforge.experimental-live-raw-result.v1",
        "task_id": "V07_GENERAL_LIVE_RATING_CLI_AND_ENGINEERING_PREVIEW_R9",
        "EXPERIMENTAL_LIVE_RATING_RUN_HASH": run_identity["EXPERIMENTAL_LIVE_RATING_RUN_HASH"],
        "engineering_case_id": case.engineering_case_id,
        "candidate_id": native.candidate_id,
        "rating_request_hash": native.rating_request_hash,
        "mesh_level": mesh_level,
        "mesh_status": mesh.get("status"),
        "mesh_result_hash": mesh.get("mesh_result_hash"),
        "constraint_preview": constraint_preview,
        "mesh": mesh,
        "mesh_observables": experimental_mesh.get("mesh_observables"),
        "total_numerical_seconds": total_seconds,
        "report_json_path": str(report_paths[0]),
        "report_md_path": str(report_paths[1]),
        "failure_code": mesh.get("failure_code"),
    }
    raw_path = output_dir / "RAW_RESULT.json"
    raw_path.write_text(json.dumps(raw, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    raw_sha = _sha256_file(raw_path)

    manifest_entries: dict[str, str] = {}
    for name in (
        "GENERAL_ENGINEERING_CASE.json",
        "EXPERIMENTAL_LIVE_RATING_RUN_IDENTITY.json",
        "CANDIDATE_SELECTION_RESULT.json",
        "NATIVE_THERMAL_BOUNDARY.json",
        "REAL_N1_MESH_RESULT.json",
        "REAL_N1_BLOCKED_RESULT.json",
        "EXPERIMENTAL_CONSTRAINT_PREVIEW.json",
        "ENGINEERING_REPORT.json",
        "ENGINEERING_REPORT.md",
        "RAW_RESULT.json",
    ):
        path = output_dir / name
        if path.is_file():
            manifest_entries[name] = _sha256_file(path)

    (output_dir / "EVIDENCE_MANIFEST.json").write_text(
        json.dumps(
            {
                "schema_version": "hxforge.evidence-manifest.v1",
                "task_id": "V07_GENERAL_LIVE_RATING_CLI_AND_ENGINEERING_PREVIEW_R9",
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

    return ExperimentalLiveRatingOutcome(
        status="EXPERIMENTAL_COMPLETE" if numeric_valid else "EXPERIMENTAL_BLOCKED",
        engineering_case_id=case.engineering_case_id,
        output_dir=output_dir,
        raw_result_path=raw_path,
        raw_result_sha256=raw_sha,
        mesh_status=str(mesh.get("status")),
        total_numerical_seconds=total_seconds,
        blocker_code=mesh.get("failure_code") if not numeric_valid else None,
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
    )


def run_experimental_live_rating_from_paths(
    input_path: Path,
    output_dir: Path,
    *,
    mesh_level: int = 1,
) -> ExperimentalLiveRatingOutcome:
    case = load_general_engineering_case_json(input_path.read_text(encoding="utf-8"))
    return run_experimental_live_rating_workflow(
        case, output_dir, mesh_level=mesh_level, enable_ephemeral_tp_cache=False
    )
