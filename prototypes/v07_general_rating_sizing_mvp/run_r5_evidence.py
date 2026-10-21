"""Unified R5 evidence: candidate selection, n=2 mesh, performance, n1/n2 compare."""

# ruff: noqa: E501

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from hexagent.exchangers.shell_tube.task173_integrated_rating.models import MeshObservables
from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
    enumerate_experimental_rating_candidates,
    selection_to_json,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    load_general_engineering_case_json,
)
from prototypes.v07_general_rating_sizing_mvp.frozen_r4_n1 import load_frozen_r4_n1_mesh
from prototypes.v07_general_rating_sizing_mvp.mesh_comparison import compare_frozen_n1_to_n2_mesh
from prototypes.v07_general_rating_sizing_mvp.positive_duty_cell import (
    build_native_cell_context,
    run_mesh_numeric_with_profile,
)
from prototypes.v07_general_rating_sizing_mvp.preflight import enumerate_task168_candidates
from prototypes.v07_general_rating_sizing_mvp.report import write_engineering_reports
from prototypes.v07_general_rating_sizing_mvp.sizing_request_builder import (
    build_task173_sizing_request,
)

R5_CASE = Path(__file__).resolve().parent / "cases" / "mvp_tube_hot_shell_cold_r5.json"
_DEFAULT_EVIDENCE_DIR = "docs/tasks/evidence/V07-GENERAL-RATING-MESH-N2-AND-PERFORMANCE-R5"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    frozen_n1 = load_frozen_r4_n1_mesh()
    case = load_general_engineering_case_json(R5_CASE.read_text(encoding="utf-8"))
    preflight = enumerate_task168_candidates(build_task173_sizing_request(case))
    (output_dir / "TASK168_PREFLIGHT.json").write_text(
        json.dumps(preflight, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    selection = enumerate_experimental_rating_candidates(case)
    (output_dir / "CANDIDATE_SELECTION_RESULT.json").write_text(
        json.dumps(selection_to_json(selection), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    milestones: dict[str, Any] = {
        "PREFLIGHT_COMPLETE": preflight.get("status") == "VALID",
        "CANDIDATE_SELECTED": selection.status == "SELECTED",
        "LOW_MESH_NUMERIC_VALID": False,
        "MESH_N2_NUMERIC_VALID": False,
        "MESH_COMPARISON_AVAILABLE": False,
        "FULL_RATING_CONVERGED": False,
        "SIZING_EVALUATED": False,
    }
    if selection.selected_candidate_id is None:
        raw = {
            "schema_version": "hxforge.general-r5-raw-result.v1",
            "status": "BLOCKED_CANDIDATE_SELECTION",
            "milestones": milestones,
        }
        (output_dir / "RAW_RESULT.json").write_text(
            json.dumps(raw, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return raw

    native = build_native_cell_context(case, selection=selection)
    mesh_n2, profile = run_mesh_numeric_with_profile(native, subdivisions=2)
    (output_dir / "MESH_N2_RESULT.json").write_text(
        json.dumps(mesh_n2, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "SOLVER_PERFORMANCE_PROFILE.json").write_text(
        json.dumps(profile, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    milestones["MESH_N2_NUMERIC_VALID"] = bool(mesh_n2.get("low_mesh_numeric_valid"))
    milestones["LOW_MESH_NUMERIC_VALID"] = True

    comparison: dict[str, Any] | None = None
    if mesh_n2.get("status") == "NUMERIC_VALID":
        obs = MeshObservables.model_validate(mesh_n2["mesh_observables"])
        comparison = compare_frozen_n1_to_n2_mesh(
            frozen_n1,
            obs,
            fine_mesh_hash=mesh_n2["mesh_result_hash"],
            fine_subdivisions=int(mesh_n2["mesh_level"]),
            candidate_id=native.candidate_id,
            rating_request_hash=native.rating_request_hash,
        )
        (output_dir / "MESH_N1_N2_COMPARISON.json").write_text(
            json.dumps(comparison, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        milestones["MESH_COMPARISON_AVAILABLE"] = comparison.get("comparable", False)

    frozen_n1_row = {
        "mesh_level": frozen_n1.mesh_level,
        "source": "R4_FROZEN",
        "mesh_result_hash": frozen_n1.mesh_result_hash,
        "total_duty_w": str(frozen_n1.total_duty_w),
        "energy_balance_residual_w": str(frozen_n1.energy_balance_residual_w),
        "terminal_boundary_residual_k": str(frozen_n1.terminal_boundary_residual_k),
        "task172_local_evaluation_count": frozen_n1.task172_local_evaluation_count,
        "wall_seconds": str(frozen_n1.wall_seconds),
    }
    mesh_levels = [frozen_n1_row]
    if mesh_n2.get("status") == "NUMERIC_VALID":
        mesh_levels.append(
            {
                "mesh_level": mesh_n2["mesh_level"],
                "source": "R5_NATIVE_RUN",
                "mesh_result_hash": mesh_n2["mesh_result_hash"],
                "total_duty_w": mesh_n2["total_duty_w"],
                "energy_balance_residual_w": mesh_n2["energy_balance_residual_w"],
                "terminal_boundary_residual_k": mesh_n2["terminal_boundary_residual_k"],
                "task172_local_evaluation_count": mesh_n2["task172_local_evaluation_count"],
                "wall_seconds": mesh_n2["wall_seconds"],
            }
        )
    experimental_mesh = {
        "full_rating_converged": False,
        "low_mesh_numeric_valid": milestones["LOW_MESH_NUMERIC_VALID"],
        "mesh_comparison_available": milestones["MESH_COMPARISON_AVAILABLE"],
        "frozen_r4_n1": frozen_n1_row,
        "mesh_levels": mesh_levels,
        "mesh_comparison": comparison,
    }
    report_paths = write_engineering_reports(
        case,
        preflight=preflight,
        sizing_outcome=None,
        output_dir=output_dir,
        workflow_status="PARTIAL_RATING_ACCEPTED"
        if milestones["MESH_N2_NUMERIC_VALID"]
        else "PARTIAL_RATING_BLOCKED",
        experimental_mesh=experimental_mesh,
    )
    total_seconds = round(time.perf_counter() - t0, 3)
    raw: dict[str, Any] = {
        "schema_version": "hxforge.general-r5-raw-result.v1",
        "engineering_case_id": case.engineering_case_id,
        "candidate_id": native.candidate_id,
        "candidate_rating_request_hash": native.rating_request_hash,
        "r4_n1_mesh_hash": frozen_n1.mesh_result_hash,
        "milestones": milestones,
        "n2_status": mesh_n2.get("status"),
        "n2_mesh_result_hash": mesh_n2.get("mesh_result_hash"),
        "n2_duty_w": mesh_n2.get("total_duty_w"),
        "n2_energy_residual_w": mesh_n2.get("energy_balance_residual_w"),
        "n2_terminal_residual_k": mesh_n2.get("terminal_boundary_residual_k"),
        "n2_task172_evaluations": mesh_n2.get("task172_local_evaluation_count"),
        "n2_numerical_seconds": mesh_n2.get("wall_seconds"),
        "solver_performance_profile": profile,
        "mesh_comparison_status": comparison.get("mesh_comparison_status") if comparison else None,
        "total_numerical_seconds": total_seconds,
        "report_json_path": str(report_paths[0]),
        "report_md_path": str(report_paths[1]),
        "production_design_approved": False,
        "numerical_authority_status": "CANDIDATE",
    }
    (output_dir / "RAW_RESULT.json").write_text(
        json.dumps(raw, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    manifest_entries: dict[str, str] = {}
    for name in (
        "CANDIDATE_SELECTION_RESULT.json",
        "MESH_N2_RESULT.json",
        "MESH_N1_N2_COMPARISON.json",
        "SOLVER_PERFORMANCE_PROFILE.json",
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
                "task_id": "V07_GENERAL_RATING_MESH_N2_AND_PERFORMANCE_R5",
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
