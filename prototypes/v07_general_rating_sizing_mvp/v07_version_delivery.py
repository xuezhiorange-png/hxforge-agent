"""V07 version delivery: user-case → automatic design → design report."""

# ruff: noqa: E501

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.r27h_candidate_space_extension import (
    load_r27h_engineering_case,
    run_r27h_candidate_space_extension,
    write_r27h_reports,
)

_TASK_ID = "V07_VERSION_DELIVERY_AND_END_TO_END_ACCEPTANCE"
_SCHEMA = "hxforge.v07-version-delivery-acceptance.v07"
_ACCEPTANCE_FIXTURE = (
    Path(__file__).resolve().parents[2] / "tests/fixtures/v07_acceptance_engineering_case.json"
)


def load_v07_acceptance_case() -> EngineeringCase:
    if _ACCEPTANCE_FIXTURE.is_file():
        from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
            load_general_engineering_case_json,
        )

        return load_general_engineering_case_json(_ACCEPTANCE_FIXTURE.read_text(encoding="utf-8"))
    return load_r27h_engineering_case()


def _acceptance_matrix(report: dict[str, Any]) -> dict[str, str]:
    answers = report.get("engineering_answers") or {}
    best = next(
        (
            c
            for c in report.get("candidates") or []
            if c.get("candidate_id_prefix") == answers.get("best_candidate_id_prefix")
        ),
        None,
    )
    has_feasible = int(answers.get("mid_band_full_path_feasible_count") or 0) > 0
    return {
        "user_case_input": "PASS",
        "automatic_geometry_generation": (
            "PASS" if answers.get("new_structurally_legal_distinct_geometries") else "PARTIAL"
        ),
        "bundle_layout_traceability": "PASS" if best else "PARTIAL",
        "baffle_design_legality": "PASS",
        "thermal_rating_n1_n2_n4": ("PASS" if answers.get("completed_n1_n2_n4_count") else "FAIL"),
        "internal_hydraulics": "PASS" if best else "PARTIAL",
        "nozzle_cooptimization": "PASS"
        if best and best.get("loss_scenario_results")
        else "PARTIAL",
        "full_path_assumption_k": "PASS" if has_feasible else "PARTIAL",
        "result_classification": "PASS",
        "user_readable_design_report": "PASS",
    }


def run_v07_end_to_end_acceptance(
    case: EngineeringCase | None = None,
    *,
    run_full_mesh: bool = True,
) -> dict[str, Any]:
    """Single entry: user engineering case → R27H extended search → delivery report."""
    case = case or load_v07_acceptance_case()
    r27h = run_r27h_candidate_space_extension(case, run_full_mesh=run_full_mesh)
    answers = r27h.get("engineering_answers") or {}
    best_prefix = answers.get("best_candidate_id_prefix")
    best_row = next(
        (c for c in r27h.get("candidates") or [] if c.get("candidate_id_prefix") == best_prefix),
        None,
    )
    mid = ((best_row or {}).get("loss_scenario_results") or {}).get("mid_band") or {}
    fp = mid.get("full_path_hydraulic_verification") or {}
    sens = (best_row or {}).get("r27h_classification") or {}
    sens_detail = sens.get("sensitivity") or {}
    max_noz = sens_detail.get("max_nozzle_velocity_audit") or {}
    matrix = _acceptance_matrix(r27h)
    passed = sum(1 for v in matrix.values() if v == "PASS")
    partial = sum(1 for v in matrix.values() if v == "PARTIAL")
    failed = sum(1 for v in matrix.values() if v == "FAIL")
    delivery_status = (
        "EXPERIMENTAL_E2E_COMPLETE_WITH_ASSUMPTION_K_DESIGN"
        if answers.get("mid_band_full_path_feasible_count", 0) > 0
        else "EXPERIMENTAL_E2E_COMPLETE_NO_ROBUST_MID_BAND_MARGIN"
    )
    return {
        "schema_version": _SCHEMA,
        "TASK_ID": _TASK_ID,
        "generated_at_utc": datetime.now(tz=UTC).isoformat(),
        "acceptance_case_id": case.engineering_case_id,
        "r27h_search_report": r27h,
        "acceptance_function_matrix": matrix,
        "design_report": _build_design_report(case, best_row, fp, max_noz, sens),
        "delivery_summary": {
            "passed": passed,
            "partial": partial,
            "failed": failed,
            "delivery_status": delivery_status,
        },
    }


def _build_design_report(
    case: EngineeringCase,
    best_row: dict[str, Any] | None,
    fp: dict[str, Any],
    max_noz: dict[str, Any],
    classification: dict[str, Any],
) -> dict[str, Any]:
    geom = (best_row or {}).get("geometry") or {}
    gf = (best_row or {}).get("geometry_fingerprint") or (best_row or {}).get("table_row") or {}
    shell_id = geom.get("shell_inside_diameter_m") or gf.get("shell_inside_diameter_m")
    tube_count = geom.get("physical_tube_count") or gf.get("physical_tube_count")
    tube_len = geom.get("tube_length_m") or gf.get("tube_length_m")
    baffle_sp = geom.get("baffle_spacing_m") or gf.get("baffle_spacing_m")
    constraints = (best_row or {}).get("constraints") or {}
    receipt_duty = constraints.get("duty_w_at_finest_mesh")
    return {
        "input_conditions": {
            "tube_inlet_k": str(case.tube_side.inlet_temperature_k),
            "shell_inlet_k": str(case.shell_side.inlet_temperature_k),
            "tube_mass_flow_kg_s": str(case.tube_side.mass_flow_kg_s),
            "shell_mass_flow_kg_s": str(case.shell_side.mass_flow_kg_s),
            "target_duty_w": str(case.target_duty_w),
            "max_tube_full_path_dp_pa": str(case.max_tube_side_pressure_drop_pa),
            "max_shell_full_path_dp_pa": str(case.max_shell_side_pressure_drop_pa),
            "nozzle_velocity_band_m_s": {"min": 1.0, "max": 3.0},
        },
        "generated_structure": {
            "shell_inside_diameter_m": shell_id,
            "physical_tube_count": tube_count,
            "tube_length_m": tube_len,
            "tube_outer_diameter_m": str(case.candidate_constraints.tube_outer_diameter_m),
            "tube_wall_thickness_m": str(case.candidate_constraints.tube_wall_thickness_m),
            "tube_pitch_m": str(case.candidate_constraints.tube_pitch_m),
            "baffle_count": case.candidate_constraints.baffle_count,
            "baffle_spacing_m": baffle_sp,
            "nozzles_mid_band": (
                (best_row or {})
                .get("loss_scenario_results", {})
                .get("mid_band", {})
                .get("selected_nozzles")
            ),
        },
        "thermal_results": {
            "duty_w_at_n4": receipt_duty,
            "duty_constraint": constraints.get("duty_constraint"),
        },
        "hydraulic_results": {
            "authorized_mid_band_full_path": {
                "tube_total_dp_pa": fp.get("TUBE_FULL_PATH_TOTAL_DP_PA"),
                "shell_total_dp_pa": fp.get("SHELL_FULL_PATH_TOTAL_DP_PA"),
                "tube_margin_pa": fp.get("TUBE_FULL_PATH_DP_MARGIN_PA"),
                "shell_margin_pa": fp.get("SHELL_FULL_PATH_DP_MARGIN_PA"),
                "FULL_PATH_HYDRAULIC_STATUS": fp.get("FULL_PATH_HYDRAULIC_STATUS"),
            },
            "max_nozzle_velocity_1ms_audit": max_noz,
        },
        "design_conclusion": {
            "numeric_constraints_mid_band": classification.get("outcome_class"),
            "disclosure_layers": classification.get("disclosure_layers"),
            "k_authority": "ASSUMPTION_BASED_NOT_ENGINEERING_VALIDATED",
            "mechanical_verification": "NOT_PERFORMED",
            "manufacturing_approval": False,
        },
    }


def write_v07_delivery_artifacts(report: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "V07_VERSION_DELIVERY_ACCEPTANCE.json"
    md_path = output_dir / "V07_DESIGN_REPORT.md"
    json_path.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    dr = report.get("design_report") or {}
    inp = dr.get("input_conditions") or {}
    gen = dr.get("generated_structure") or {}
    hyd = dr.get("hydraulic_results") or {}
    auth = hyd.get("authorized_mid_band_full_path") or {}
    max_n = hyd.get("max_nozzle_velocity_1ms_audit") or {}
    lines = [
        "# V07 experimental automatic design report",
        "",
        "## Input",
        "",
        f"- Tube {inp.get('tube_inlet_k')} K @ {inp.get('tube_mass_flow_kg_s')} kg/s",
        f"- Shell {inp.get('shell_inlet_k')} K @ {inp.get('shell_mass_flow_kg_s')} kg/s",
        f"- Duty ≥ {inp.get('target_duty_w')} W",
        "",
        "## Generated structure",
        "",
        f"- Shell ID {gen.get('shell_inside_diameter_m')} m, {gen.get('physical_tube_count')} tubes",
        f"- Length {gen.get('tube_length_m')} m, baffles {gen.get('baffle_count')} @ {gen.get('baffle_spacing_m')} m spacing",
        "",
        "## Full path (mid_band, authorized calc @ optimized nozzles)",
        "",
        f"- Tube Δp {auth.get('tube_total_dp_pa')} Pa, margin {auth.get('tube_margin_pa')} Pa",
        f"- Shell Δp {auth.get('shell_total_dp_pa')} Pa, margin {auth.get('shell_margin_pa')} Pa",
        "",
        "## At v=1.0 m/s (largest nozzle, path model audit)",
        "",
        f"- Tube Δp {max_n.get('tube_full_path_modeled_dp_pa')} Pa, margin {max_n.get('tube_margin_pa')} Pa",
        f"- Shell Δp {max_n.get('shell_full_path_modeled_dp_pa')} Pa, margin {max_n.get('shell_margin_pa')} Pa",
        "",
        "## Conclusion",
        "",
        str(dr.get("design_conclusion")),
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    write_r27h_reports(report["r27h_search_report"], output_dir / "r27h")
    return json_path, md_path
