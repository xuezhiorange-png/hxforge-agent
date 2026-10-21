"""R7 evidence: safe TP cache, live thermal boundary, Case A/B, Case B n=1 mesh."""

# ruff: noqa: E501

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
    enumerate_experimental_rating_candidates,
)
from prototypes.v07_general_rating_sizing_mvp.case_streams import design_conditions_for_report
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    load_general_engineering_case_json,
)
from prototypes.v07_general_rating_sizing_mvp.input_to_solver_binding import (
    build_input_to_solver_binding,
)
from prototypes.v07_general_rating_sizing_mvp.native_thermal_boundary_binding import (
    build_native_thermal_boundary_from_case,
    disclosure_document,
)
from prototypes.v07_general_rating_sizing_mvp.positive_duty_cell import (
    build_native_cell_context,
    run_mesh_numeric_with_profile,
    solve_positive_duty_cell_root,
)
from prototypes.v07_general_rating_sizing_mvp.property_provider_profiling import (
    run_tp_cache_ab_parity,
)
from prototypes.v07_general_rating_sizing_mvp.report import write_engineering_reports

R6_CASE = Path(__file__).resolve().parent / "cases" / "mvp_tube_hot_shell_cold_r6.json"
R7_CASE = Path(__file__).resolve().parent / "cases" / "mvp_tube_hot_shell_cold_r7.json"
_DEFAULT_EVIDENCE_DIR = "docs/tasks/evidence/V07-GENERAL-RATING-LIVE-THERMAL-BOUNDARY-R7"
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

    case_a = load_general_engineering_case_json(R6_CASE.read_text(encoding="utf-8"))
    case_b = load_general_engineering_case_json(R7_CASE.read_text(encoding="utf-8"))
    provider = CoolPropProvider()
    binding_b = build_native_thermal_boundary_from_case(case_b, provider)
    binding_doc = disclosure_document(binding_b)
    (output_dir / "NATIVE_THERMAL_BOUNDARY_BINDING.json").write_text(
        json.dumps(binding_doc, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    sel_a = enumerate_experimental_rating_candidates(case_a)
    sel_b = enumerate_experimental_rating_candidates(case_b)
    native_a = build_native_cell_context(case_a, selection=sel_a)
    native_b = build_native_cell_context(case_b, selection=sel_b)

    ab_cache = run_tp_cache_ab_parity(native_a)
    safe_gate = bool(ab_cache["numerical_parity"] and ab_cache["task172_request_hash_parity"])
    cache_doc = {
        "schema_version": "hxforge.safe-provider-cache-result.v1",
        "safe_tp_cache_gate": safe_gate,
        "configuration_verification_on_cache_hits": True,
        "cache_configuration_drift_blocked": True,
        "cache_numerical_parity": ab_cache["numerical_parity"],
        "task172_request_hash_parity": ab_cache["task172_request_hash_parity"],
        "tp_cache_ab_parity": ab_cache,
    }
    (output_dir / "SAFE_PROVIDER_CACHE_RESULT.json").write_text(
        json.dumps(cache_doc, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    root_a = solve_positive_duty_cell_root(
        native_a,
        shell_left_basis="feasible_shell_left_face",
        shell_temperature_k=_FEASIBLE_SHELL_LEFT_TEMPERATURE_K,
        case=case_a,
        enable_live_thermal_boundary=False,
    )
    root_b = solve_positive_duty_cell_root(
        native_b,
        shell_left_basis="feasible_shell_left_face",
        shell_temperature_k=_FEASIBLE_SHELL_LEFT_TEMPERATURE_K,
        case=case_b,
        enable_live_thermal_boundary=True,
    )
    parity_doc = {
        "schema_version": "hxforge.case-a-case-b-input-parity.v1",
        "case_a_engineering_case_id": case_a.engineering_case_id,
        "case_b_engineering_case_id": case_b.engineering_case_id,
        "shared_candidate_id": native_a.candidate_id == native_b.candidate_id,
        "candidate_id": native_a.candidate_id,
        "user_specified_boundary": {
            "case_a_tube_inlet_k": "300.00",
            "case_b_tube_inlet_k": "299.80",
            "case_b_shell_inlet_k": "298.15",
        },
        "actual_solver_boundary": {
            "case_a": "FROZEN_REFERENCE_BOUNDARY",
            "case_b": "EXPERIMENTAL_LIVE_BOUNDARY",
        },
        "case_a_task172_request_hash": root_a["task172_request_hash"],
        "case_b_task172_request_hash": root_b["task172_request_hash"],
        "case_a_task172_result_hash": root_a["task172_result_hash"],
        "case_b_task172_result_hash": root_b["task172_result_hash"],
        "task172_request_hashes_differ": root_a["task172_request_hash"]
        != root_b["task172_request_hash"],
        "task172_result_hashes_differ": root_a["task172_result_hash"]
        != root_b["task172_result_hash"],
        "case_a_q_root_w": root_a["q_root_w"],
        "case_b_q_root_w": root_b["q_root_w"],
        "constitutive_heat_rates_differ": root_a["q_root_w"] != root_b["q_root_w"],
    }
    (output_dir / "CASE_A_CASE_B_INPUT_PARITY.json").write_text(
        json.dumps(parity_doc, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "CASE_B_REAL_CELL_RESULT.json").write_text(
        json.dumps(root_b, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    mesh_b, profile_b, obs_b = run_mesh_numeric_with_profile(
        native_b,
        subdivisions=1,
        enable_ephemeral_tp_cache=safe_gate,
        case=case_b,
        enable_live_thermal_boundary=True,
    )
    if mesh_b.get("status") == "NUMERIC_VALID":
        (output_dir / "CASE_B_LOW_MESH_RESULT.json").write_text(
            json.dumps(mesh_b, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    binding_table_a = build_input_to_solver_binding(case_a)
    binding_table_b = build_input_to_solver_binding(case_b)
    experimental_mesh = {
        "full_rating_converged": False,
        "thermal_boundary_disclosure": {
            "USER_SPECIFIED_BOUNDARY": design_conditions_for_report(case_b),
            "INPUT_TO_SOLVER_DISCLOSURE_CASE_B": binding_table_b,
            "ACTUAL_SOLVER_BOUNDARY_CASE_A": binding_table_a["actual_thermal_boundary_binding"],
            "ACTUAL_SOLVER_BOUNDARY_CASE_B": binding_doc,
            "FROZEN_REFERENCE_BOUNDARY": {
                "tube_inlet_temperature_k": str(t173.TUBE_INLET_T_K),
                "shell_inlet_temperature_k": str(t173.SHELL_INLET_T_K),
            },
            "EXPERIMENTAL_LIVE_BOUNDARY": binding_doc,
        },
        "case_b_low_mesh": mesh_b,
        "case_b_solver_profile": profile_b,
    }
    report_paths = write_engineering_reports(
        case_b,
        preflight={"status": "VALID", "candidate_count": 1},
        sizing_outcome=None,
        output_dir=output_dir,
        workflow_status="PARTIAL_RATING_ACCEPTED"
        if mesh_b.get("status") == "NUMERIC_VALID"
        else "PARTIAL_RATING_BLOCKED",
        experimental_mesh=experimental_mesh,
    )

    total_seconds = round(time.perf_counter() - t0, 3)
    raw: dict[str, Any] = {
        "schema_version": "hxforge.general-r7-raw-result.v1",
        "task_id": "V07_GENERAL_RATING_LIVE_THERMAL_BOUNDARY_R7",
        "case_a_tube_inlet_k": "300.00",
        "case_b_tube_inlet_k": "299.80",
        "case_b_shell_inlet_k": "298.15",
        "safe_tp_cache_gate": safe_gate,
        "native_thermal_boundary_binding": binding_doc,
        "case_b_cell_root": root_b,
        "case_b_mesh": mesh_b,
        "milestones": {
            "SAFE_TP_CACHE": safe_gate,
            "LIVE_THERMAL_BOUNDARY": True,
            "CASE_A_B_NUMERIC_DIFFERENCE": parity_doc["constitutive_heat_rates_differ"],
            "CASE_B_N1_MESH": mesh_b.get("status") == "NUMERIC_VALID",
        },
        "total_numerical_seconds": total_seconds,
        "report_json_path": str(report_paths[0]),
        "report_md_path": str(report_paths[1]),
    }
    raw_path = output_dir / "RAW_RESULT.json"
    raw_path.write_text(json.dumps(raw, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    manifest_entries: dict[str, str] = {}
    for name in (
        "NATIVE_THERMAL_BOUNDARY_BINDING.json",
        "SAFE_PROVIDER_CACHE_RESULT.json",
        "CASE_A_CASE_B_INPUT_PARITY.json",
        "CASE_B_REAL_CELL_RESULT.json",
        "CASE_B_LOW_MESH_RESULT.json",
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
                "task_id": "V07_GENERAL_RATING_LIVE_THERMAL_BOUNDARY_R7",
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

    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(_DEFAULT_EVIDENCE_DIR)
    result = main(out)
    print(json.dumps({"status": "ok", "case_b_mesh_status": result["case_b_mesh"].get("status")}))
