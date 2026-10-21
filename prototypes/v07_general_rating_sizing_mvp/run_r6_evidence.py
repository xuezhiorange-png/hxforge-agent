"""R6 evidence: dependency parity note, TP profiling, n=4 mesh, n2/n4 compare."""

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
from prototypes.v07_general_rating_sizing_mvp.frozen_r4_n1 import load_frozen_r4_n1_mesh
from prototypes.v07_general_rating_sizing_mvp.frozen_r5_n2 import load_frozen_r5_n2_mesh
from prototypes.v07_general_rating_sizing_mvp.mesh_comparison import compare_mesh_observables_duty
from prototypes.v07_general_rating_sizing_mvp.physical_model_parity import (
    build_physical_model_fingerprint,
    compare_physical_fingerprints,
)
from prototypes.v07_general_rating_sizing_mvp.positive_duty_cell import (
    build_native_cell_context,
    run_mesh_numeric_with_profile,
)
from prototypes.v07_general_rating_sizing_mvp.property_provider_profiling import (
    profile_representative_cell_tp_calls,
    run_tp_cache_ab_parity,
)
from prototypes.v07_general_rating_sizing_mvp.report import write_engineering_reports

R4_CASE = Path(__file__).resolve().parent / "cases" / "mvp_tube_hot_shell_cold_r4.json"
R5_CASE = Path(__file__).resolve().parent / "cases" / "mvp_tube_hot_shell_cold_r5.json"
R6_CASE = Path(__file__).resolve().parent / "cases" / "mvp_tube_hot_shell_cold_r6.json"
_DEFAULT_EVIDENCE_DIR = "docs/tasks/evidence/V07-GENERAL-RATING-N4-PERFORMANCE-AND-MESH-R6"

R4_FROZEN_RATING_HASH = "68a84ce8f4fd3c4af3c6dea8f31929f4781add2403251b02c25ac355456403e4"
R5_FROZEN_RATING_HASH = "68c58febc2ad50e0266cc03811ce3c6ff59ef5bdbfbe3f0b4e322f92836f9c28"
R5_BASELINE_PROVIDER_CALLS = 290586


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
    frozen_n2 = load_frozen_r5_n2_mesh()

    r4_case = load_general_engineering_case_json(R4_CASE.read_text(encoding="utf-8"))
    r5_case = load_general_engineering_case_json(R5_CASE.read_text(encoding="utf-8"))
    r6_case = load_general_engineering_case_json(R6_CASE.read_text(encoding="utf-8"))

    r4_sel = enumerate_experimental_rating_candidates(r4_case)
    r5_sel = enumerate_experimental_rating_candidates(r5_case)
    r6_sel = enumerate_experimental_rating_candidates(r6_case)
    r4_native = build_native_cell_context(r4_case, selection=r4_sel)
    r5_native = build_native_cell_context(r5_case, selection=r5_sel)
    fp_r4 = build_physical_model_fingerprint(r4_case, r4_native)
    fp_r5 = build_physical_model_fingerprint(r5_case, r5_native)
    fp_r6 = build_physical_model_fingerprint(r6_case, build_native_cell_context(r6_case, selection=r6_sel))
    parity = compare_physical_fingerprints(fp_r4, fp_r5)
    parity_doc = {
        **parity,
        "r4_frozen_rating_request_hash": R4_FROZEN_RATING_HASH,
        "r5_frozen_rating_request_hash": R5_FROZEN_RATING_HASH,
        "r4_built_rating_request_hash": r4_native.rating_request_hash,
        "r5_built_rating_request_hash": r5_native.rating_request_hash,
        "r6_built_rating_request_hash": fp_r6["metadata_only_projection"]["candidate_rating_request_hash"],
        "physical_model_fingerprint_r4": fp_r4["physical_model_fingerprint_sha256"],
        "physical_model_fingerprint_r5": fp_r5["physical_model_fingerprint_sha256"],
        "physical_model_fingerprint_r6": fp_r6["physical_model_fingerprint_sha256"],
        "r4_r5_r6_physical_match": (
            fp_r4["physical_model_fingerprint_sha256"]
            == fp_r5["physical_model_fingerprint_sha256"]
            == fp_r6["physical_model_fingerprint_sha256"]
        ),
        "r5_n1_n2_duty_comparison_clarification": (
            "Historical R5 mesh_comparison_status PASS is duty-only; "
            "full_mesh_comparison_status was NOT_AVAILABLE_WALL_EXTREMA_NOT_ARCHIVED."
        ),
    }
    (output_dir / "PHYSICAL_MODEL_PARITY.json").write_text(
        json.dumps(parity_doc, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    r6_native = build_native_cell_context(r6_case, selection=r6_sel)
    tp_profile = profile_representative_cell_tp_calls(r6_native)
    (output_dir / "PROPERTY_PROVIDER_CALL_PROFILE.json").write_text(
        json.dumps(tp_profile, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    ab = run_tp_cache_ab_parity(r6_native)
    optimization_implemented = bool(ab["numerical_parity"]) and ab["cache_stats"]["cache_hits"] > 0
    perf_doc = {
        "schema_version": "hxforge.performance-baseline-and-optimization.v1",
        "r5_baseline_n2_wall_seconds": str(frozen_n2.wall_seconds),
        "r5_baseline_task172_evaluations": frozen_n2.task172_local_evaluation_count,
        "r5_baseline_property_provider_state_lookups": R5_BASELINE_PROVIDER_CALLS,
        "r5_unique_task172_request_count": "NOT_MEASURED",
        "representative_cell_tp_profile": tp_profile,
        "tp_cache_ab_parity": ab,
        "optimization_implemented": optimization_implemented,
        "optimization_numerical_parity": ab["numerical_parity"],
        "provider_call_reduction_percent": ab["provider_call_reduction_percent"],
        "wall_time_reduction_percent": ab["wall_time_reduction_percent"],
    }
    (output_dir / "PERFORMANCE_BASELINE_AND_OPTIMIZATION.json").write_text(
        json.dumps(perf_doc, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    mesh_n4, profile_n4, mesh_n4_obs = run_mesh_numeric_with_profile(
        r6_native,
        subdivisions=4,
        enable_ephemeral_tp_cache=optimization_implemented,
    )
    (output_dir / "MESH_N4_RESULT.json").write_text(
        json.dumps(mesh_n4, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    n2_n4_comparison: dict[str, Any] | None = None
    physical_parity_ok = parity_doc["r4_r5_r6_physical_match"]
    if mesh_n4.get("status") == "NUMERIC_VALID" and mesh_n4_obs is not None and physical_parity_ok:
        n2_n4_comparison = compare_mesh_observables_duty(
            frozen_n2.total_duty_w,
            frozen_n2.terminal_boundary_residual_k,
            mesh_n4_obs,
            coarse_mesh_hash=frozen_n2.mesh_result_hash,
            fine_mesh_hash=mesh_n4["mesh_result_hash"],
            coarse_level=2,
            fine_level=4,
            comparable=True,
        )
        (output_dir / "MESH_N2_N4_COMPARISON.json").write_text(
            json.dumps(n2_n4_comparison, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    mesh_levels = [
        {
            "mesh_level": 1,
            "source": "R4_FROZEN",
            "mesh_result_hash": frozen_n1.mesh_result_hash,
            "total_duty_w": str(frozen_n1.total_duty_w),
            "energy_balance_residual_w": str(frozen_n1.energy_balance_residual_w),
            "terminal_boundary_residual_k": str(frozen_n1.terminal_boundary_residual_k),
            "task172_local_evaluation_count": frozen_n1.task172_local_evaluation_count,
            "wall_seconds": str(frozen_n1.wall_seconds),
        },
        {
            "mesh_level": 2,
            "source": "R5_FROZEN",
            "mesh_result_hash": frozen_n2.mesh_result_hash,
            "total_duty_w": str(frozen_n2.total_duty_w),
            "energy_balance_residual_w": str(frozen_n2.energy_balance_residual_w),
            "terminal_boundary_residual_k": str(frozen_n2.terminal_boundary_residual_k),
            "task172_local_evaluation_count": frozen_n2.task172_local_evaluation_count,
            "wall_seconds": str(frozen_n2.wall_seconds),
        },
    ]
    if mesh_n4.get("status") == "NUMERIC_VALID":
        mesh_levels.append(
            {
                "mesh_level": 4,
                "source": "R6_NATIVE_RUN",
                "mesh_result_hash": mesh_n4["mesh_result_hash"],
                "total_duty_w": mesh_n4["total_duty_w"],
                "energy_balance_residual_w": mesh_n4["energy_balance_residual_w"],
                "terminal_boundary_residual_k": mesh_n4["terminal_boundary_residual_k"],
                "task172_local_evaluation_count": mesh_n4["task172_local_evaluation_count"],
                "wall_seconds": mesh_n4["wall_seconds"],
            }
        )

    experimental_mesh = {
        "full_rating_converged": False,
        "low_mesh_numeric_valid": True,
        "mesh_comparison_available": n2_n4_comparison is not None,
        "frozen_r4_n1": mesh_levels[0],
        "mesh_levels": mesh_levels,
        "mesh_comparison": n2_n4_comparison,
        "performance_optimization": perf_doc,
        "engineering_gates_not_met": [
            "FULL_MESH_LADDER_CONVERGENCE",
            "PRODUCTION_SIZING_AND_RANKING",
            "WALL_EXTREMA_MESH_COMPARISON_WITHOUT_ARCHIVED_OBSERVABLES",
        ],
    }
    report_paths = write_engineering_reports(
        r6_case,
        preflight={"status": "VALID", "candidate_count": 1},
        sizing_outcome=None,
        output_dir=output_dir,
        workflow_status="PARTIAL_RATING_ACCEPTED"
        if mesh_n4.get("status") == "NUMERIC_VALID"
        else "PARTIAL_RATING_BLOCKED",
        experimental_mesh=experimental_mesh,
    )

    total_seconds = round(time.perf_counter() - t0, 3)
    raw: dict[str, Any] = {
        "schema_version": "hxforge.general-r6-raw-result.v1",
        "engineering_case_id": r6_case.engineering_case_id,
        "candidate_id": r6_native.candidate_id,
        "physical_model_fingerprint": fp_r6["physical_model_fingerprint_sha256"],
        "r4_r5_physical_parity": parity_doc["r4_r5_physical_parity"],
        "optimization_implemented": optimization_implemented,
        "n4_status": mesh_n4.get("status"),
        "n4_mesh_result_hash": mesh_n4.get("mesh_result_hash"),
        "n4_duty_w": mesh_n4.get("total_duty_w"),
        "n4_energy_residual_w": mesh_n4.get("energy_balance_residual_w"),
        "n4_terminal_residual_k": mesh_n4.get("terminal_boundary_residual_k"),
        "n4_task172_evaluations": mesh_n4.get("task172_local_evaluation_count"),
        "n4_numerical_seconds": mesh_n4.get("wall_seconds"),
        "n4_solver_profile": profile_n4,
        "n2_n4_duty_comparison": (
            n2_n4_comparison.get("duty_comparison_status") if n2_n4_comparison else None
        ),
        "full_mesh_comparison": "NOT_AVAILABLE",
        "milestones": {
            "PHYSICAL_MODEL_PARITY_DOCUMENTED": True,
            "PERFORMANCE_ANALYSIS_COMPLETE": True,
            "MESH_N4_EXECUTED": True,
            "MESH_N4_NUMERIC_VALID": mesh_n4.get("status") == "NUMERIC_VALID",
            "MESH_N2_N4_COMPARISON_AVAILABLE": n2_n4_comparison is not None,
            "FULL_RATING_CONVERGED": False,
        },
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
        "PHYSICAL_MODEL_PARITY.json",
        "PERFORMANCE_BASELINE_AND_OPTIMIZATION.json",
        "PROPERTY_PROVIDER_CALL_PROFILE.json",
        "MESH_N4_RESULT.json",
        "MESH_N2_N4_COMPARISON.json",
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
                "task_id": "V07_GENERAL_RATING_N4_PERFORMANCE_AND_MESH_R6",
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
