"""Unified R4 evidence: preflight, positive-duty cell, low mesh (single entry)."""

# ruff: noqa: E501

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
    enumerate_experimental_rating_candidates,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    load_general_engineering_case_json,
)
from prototypes.v07_general_rating_sizing_mvp.input_to_solver_binding import (
    build_input_to_solver_binding,
)
from prototypes.v07_general_rating_sizing_mvp.positive_duty_cell import (
    build_native_cell_context,
    run_low_mesh_numeric,
    run_positive_duty_trials,
    solve_positive_duty_cell_root,
)
from prototypes.v07_general_rating_sizing_mvp.preflight import enumerate_task168_candidates
from prototypes.v07_general_rating_sizing_mvp.report import write_engineering_reports
from prototypes.v07_general_rating_sizing_mvp.sizing_request_builder import (
    build_task173_sizing_request,
)

R4_CASE = Path(__file__).resolve().parent / "cases" / "mvp_tube_hot_shell_cold_r4.json"
_DEFAULT_EVIDENCE_DIR = (
    "docs/tasks/evidence/V07-GENERAL-RATING-POSITIVE-DUTY-CELL-AND-FIRST-MESH-R4"
)

# Shell cold inlet cannot host a positive-q bracket (F(q=0)>0, zero shell capacity margin).
# Mesh interval-0 uses a higher shell-face enthalpy during outer shooting; 298.5 K is a
# documented feasible left-face state for constitutive bracket establishment.
_FEASIBLE_SHELL_LEFT_TEMPERATURE_K = 298.5


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    case = load_general_engineering_case_json(R4_CASE.read_text(encoding="utf-8"))
    (output_dir / "ENGINEERING_CASE.json").write_text(
        case.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    binding = build_input_to_solver_binding(case)
    (output_dir / "INPUT_TO_SOLVER_BINDING.json").write_text(
        json.dumps(binding, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    milestones: dict[str, Any] = {
        "PREFLIGHT_COMPLETE": False,
        "CELL_CONSTITUTIVE_VALID": False,
        "POSITIVE_DUTY_CELL_ROOT_ACCEPTED": False,
        "LOW_MESH_NUMERIC_VALID": False,
        "PARTIAL_RATING_BLOCKED": False,
        "FULL_RATING_CONVERGED": False,
    }

    scope, detail = case.applicability_status()
    if scope == "BLOCKED":
        raw = {
            "schema_version": "hxforge.general-r4-raw-result.v1",
            "engineering_case_id": case.engineering_case_id,
            "status": "BLOCKED_INPUT",
            "detail": detail,
            "milestones": milestones,
        }
        (output_dir / "RAW_RESULT.json").write_text(
            json.dumps(raw, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return raw

    sizing_request = build_task173_sizing_request(case)
    preflight = enumerate_task168_candidates(sizing_request)
    preflight["task168_structural_admission"] = preflight.get("status") == "VALID"
    preflight["task168_downstream_rating_status"] = "NOT_RUN_UNIFIED_R4_PATH"
    preflight["task173_full_ladder_status"] = "NOT_RUN"
    (output_dir / "TASK168_PREFLIGHT.json").write_text(
        json.dumps(preflight, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    milestones["PREFLIGHT_COMPLETE"] = preflight.get("status") == "VALID"

    selection = enumerate_experimental_rating_candidates(case)
    native = build_native_cell_context(case, selection=selection)

    inlet_trials = run_positive_duty_trials(
        native,
        shell_left_basis="SHELL_COLD_INLET_BOUNDARY_NOT_CELL_FACE",
        shell_temperature_k=298.15,
        q_values_w=(0.0, 1.0, 10.0, 100.0),
    )
    feasible_qs = (50.0, 500.0, 2000.0, 4000.0, 8000.0)
    feasible_trials = run_positive_duty_trials(
        native,
        shell_left_basis="MESH_INTERVAL_0_FEASIBLE_SHELL_FACE",
        shell_temperature_k=_FEASIBLE_SHELL_LEFT_TEMPERATURE_K,
        q_values_w=feasible_qs,
    )
    trials_doc = {
        "schema_version": "hxforge.positive-duty-cell-trials-bundle.v1",
        "candidate_id": native.candidate_id,
        "shell_cold_inlet_probe": inlet_trials,
        "mesh_feasible_face_probe": feasible_trials,
        "positive_duty_original_blocker": "LOW_SIDE_DOMAIN_INFEASIBLE_AT_SHELL_COLD_INLET_WHEN_F0_POSITIVE",
    }
    (output_dir / "POSITIVE_DUTY_CELL_TRIALS.json").write_text(
        json.dumps(trials_doc, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    milestones["CELL_CONSTITUTIVE_VALID"] = (
        feasible_trials["positive_duty_task172_validated_count"] > 0
    )

    cell_root = solve_positive_duty_cell_root(
        native,
        shell_left_basis="MESH_INTERVAL_0_FEASIBLE_SHELL_FACE",
        shell_temperature_k=_FEASIBLE_SHELL_LEFT_TEMPERATURE_K,
    )
    (output_dir / "CELL_ROOT_RESULT.json").write_text(
        json.dumps(cell_root, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    milestones["POSITIVE_DUTY_CELL_ROOT_ACCEPTED"] = bool(
        cell_root.get("positive_duty_cell_root_accepted")
    )

    low_mesh = run_low_mesh_numeric(native, subdivisions=1)
    (output_dir / "LOW_MESH_RESULT.json").write_text(
        json.dumps(low_mesh, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    milestones["LOW_MESH_NUMERIC_VALID"] = bool(low_mesh.get("low_mesh_numeric_valid"))
    milestones["PARTIAL_RATING_BLOCKED"] = not milestones["FULL_RATING_CONVERGED"]

    report_paths = write_engineering_reports(
        case,
        preflight=preflight,
        sizing_outcome=None,
        output_dir=output_dir,
        workflow_status="PARTIAL_RATING_ACCEPTED"
        if milestones["LOW_MESH_NUMERIC_VALID"]
        else "PARTIAL_RATING_BLOCKED",
    )

    total_seconds = round(time.perf_counter() - t0, 3)
    raw: dict[str, Any] = {
        "schema_version": "hxforge.general-r4-raw-result.v1",
        "engineering_case_id": case.engineering_case_id,
        "engineering_case_schema": case.schema_version,
        "candidate_id": native.candidate_id,
        "candidate_hash": native.candidate_hash,
        "candidate_rating_request_hash": native.rating_request_hash,
        "milestones": milestones,
        "production_design_approved": False,
        "numerical_authority_status": "CANDIDATE",
        "total_numerical_seconds": total_seconds,
        "report_json_path": str(report_paths[0]),
        "report_md_path": str(report_paths[1]),
        "positive_duty_trial_count": feasible_trials["positive_duty_trial_count"],
        "positive_duty_task172_validated_count": feasible_trials[
            "positive_duty_task172_validated_count"
        ],
        "cell_root_duty_w": cell_root.get("q_root_w"),
        "cell_root_residual_w": cell_root.get("residual_f_q_w"),
        "mesh_level": low_mesh.get("mesh_level"),
        "mesh_duty_w": low_mesh.get("total_duty_w"),
        "mesh_energy_residual_w": low_mesh.get("energy_balance_residual_w"),
        "mesh_terminal_residual_k": low_mesh.get("terminal_boundary_residual_k"),
        "mesh_result_hash": low_mesh.get("mesh_result_hash"),
    }
    (output_dir / "RAW_RESULT.json").write_text(
        json.dumps(raw, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    manifest_entries: dict[str, str] = {}
    for name in (
        "ENGINEERING_CASE.json",
        "INPUT_TO_SOLVER_BINDING.json",
        "POSITIVE_DUTY_CELL_TRIALS.json",
        "CELL_ROOT_RESULT.json",
        "LOW_MESH_RESULT.json",
        "ENGINEERING_REPORT.json",
        "ENGINEERING_REPORT.md",
        "RAW_RESULT.json",
        "TASK168_PREFLIGHT.json",
    ):
        path = output_dir / name
        if path.is_file():
            manifest_entries[name] = _sha256_file(path)
    (output_dir / "EVIDENCE_MANIFEST.json").write_text(
        json.dumps(
            {
                "schema_version": "hxforge.evidence-manifest.v1",
                "task_id": "V07_GENERAL_RATING_POSITIVE_DUTY_CELL_AND_FIRST_MESH_R4",
                "files": manifest_entries,
                "total_numerical_seconds": total_seconds,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return raw


if __name__ == "__main__":
    import sys

    target = Path(sys.argv[1] if len(sys.argv) > 1 else _DEFAULT_EVIDENCE_DIR)
    result = main(target)
    print(json.dumps(result, indent=2))
