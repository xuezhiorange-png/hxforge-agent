"""V07 final live E2E delivery acceptance."""

# ruff: noqa: E501

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any

from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    EngineeringCase,
    load_general_engineering_case_json,
)
from prototypes.v07_general_rating_sizing_mvp.r27h_candidate_space_extension import (
    R27H_EXPERIMENTAL_GEOMETRY_TABLE,
    run_r27h_candidate_space_extension,
    write_r27h_reports,
)

_TASK_ID = "V07_FINAL_LIVE_E2E_DELIVERY_ACCEPTANCE"
_SCHEMA = "hxforge.v07-final-live-e2e-delivery.v07"
_DEFAULT_LIVE_CASE = (
    Path(__file__).resolve().parents[2] / "tests/fixtures/v07_live_acceptance_user_case.json"
)


class ExecutionMode(str, Enum):
    LIVE_COMPUTE = "LIVE_COMPUTE"
    FIXTURE_REPLAY = "FIXTURE_REPLAY"


def load_user_case_json(path: Path) -> EngineeringCase:
    if not path.is_file():
        raise FileNotFoundError(f"user case not found: {path}")
    return load_general_engineering_case_json(path.read_text(encoding="utf-8"))


def validate_user_case(case: EngineeringCase) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if case.exchanger_type != "SHELL_AND_TUBE_FIXED_TUBESHEET_SINGLE_PHASE":
        errors.append(f"unsupported exchanger_type={case.exchanger_type}")
    if str(case.tube_side.fluid) != "PURE_ORDINARY_WATER":
        errors.append("tube fluid must be PURE_ORDINARY_WATER for V07 experimental envelope")
    if str(case.shell_side.fluid) != "PURE_ORDINARY_WATER":
        errors.append("shell fluid must be PURE_ORDINARY_WATER for V07 experimental envelope")
    cc = case.candidate_constraints
    if cc.baffle_count != 4:
        warnings.append("V07 R27H table assumes baffle_count=4")
    for row in R27H_EXPERIMENTAL_GEOMETRY_TABLE:
        expected = Decimal(row["baffle_spacing_m"]) * Decimal(cc.baffle_count + 1)
        if expected != Decimal(row["tube_length_m"]):
            errors.append("R27H geometry table inconsistent with baffle_count span rule")
            break
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "declared_applicability": (
            "Experimental shell-and-tube sizing for water/water; "
            "Task168 discrete shells 0.56/0.58/0.60 and paired tube/baffle ladder."
        ),
    }


def _mesh_converged_evidence(row: dict[str, Any]) -> bool:
    ev = row.get("mesh_rating_evidence") or {}
    if ev.get("full_rating_converged") is True:
        return True
    return row.get("rating_participation_status") == "FULLY_RATED" and bool(
        row.get("loss_scenario_results")
    )


def _report_field_complete(design_report: dict[str, Any]) -> tuple[bool, list[str]]:
    missing: list[str] = []
    gen = design_report.get("generated_structure") or {}
    for key in (
        "shell_inside_diameter_m",
        "physical_tube_count",
        "tube_length_m",
        "baffle_spacing_m",
        "tube_outer_diameter_m",
    ):
        if gen.get(key) is None:
            missing.append(f"generated_structure.{key}")
    therm = design_report.get("thermal_results") or {}
    if therm.get("duty_w_at_n4") is None:
        missing.append("thermal_results.duty_w_at_n4")
    return len(missing) == 0, missing


def acceptance_matrix_strict(
    *,
    mode: ExecutionMode,
    case: EngineeringCase,
    r27h: dict[str, Any],
    design_report: dict[str, Any],
) -> dict[str, str]:
    answers = r27h.get("engineering_answers") or {}
    candidates = r27h.get("candidates") or []
    best_prefix = answers.get("best_candidate_id_prefix")
    best = next((c for c in candidates if c.get("candidate_id_prefix") == best_prefix), None)
    complete, missing = _report_field_complete(design_report)

    if mode == ExecutionMode.FIXTURE_REPLAY:
        return {
            "user_case_input": "REPLAY",
            "automatic_geometry_generation": "REPLAY",
            "bundle_layout_traceability": "REPLAY",
            "baffle_design_legality": "REPLAY",
            "thermal_rating_n1_n2_n4": "REPLAY",
            "internal_hydraulics": "REPLAY",
            "nozzle_cooptimization": "REPLAY",
            "full_path_assumption_k": "REPLAY",
            "result_classification": "REPLAY",
            "user_readable_design_report": "REPLAY",
        }

    validation = validate_user_case(case)
    rated_rows = [c for c in candidates if _mesh_converged_evidence(c)]
    has_feasible = int(answers.get("mid_band_full_path_feasible_count") or 0) > 0
    new_legal = int(answers.get("new_structurally_legal_distinct_geometries") or 0)

    def _status(ok: bool, partial: bool = False) -> str:
        if ok:
            return "PASS"
        return "PARTIAL" if partial else "FAIL"

    return {
        "user_case_input": _status(validation["valid"]),
        "automatic_geometry_generation": _status(new_legal > 0, partial=new_legal == 0),
        "bundle_layout_traceability": _status(
            best is not None and (best.get("phase_a") or {}).get("physical_tube_count") is not None
        ),
        "baffle_design_legality": _status(
            all(
                (c.get("phase_a") or {}).get("phase_a_status") != "GEOMETRY_BLOCKED"
                for c in candidates
                if c.get("table_row")
            ),
            partial=True,
        ),
        "thermal_rating_n1_n2_n4": _status(len(rated_rows) >= 1),
        "internal_hydraulics": _status(
            best is not None
            and (best.get("constraints") or {}).get("hydraulic_constraint_status") == "SATISFIED",
            partial=best is not None,
        ),
        "nozzle_cooptimization": _status(
            best is not None and bool((best.get("loss_scenario_results") or {}).get("mid_band"))
        ),
        "full_path_assumption_k": _status(has_feasible, partial=bool(rated_rows)),
        "result_classification": _status(
            best is not None
            and (best.get("r27h_classification") or {}).get("outcome_class")
            not in ("FULL_PATH_NOT_FEASIBLE", "RATING_INCOMPLETE")
            if has_feasible
            else best is not None,
            partial=not has_feasible,
        ),
        "user_readable_design_report": _status(complete, partial=not missing),
    }


def run_v07_live_e2e(
    case: EngineeringCase,
    *,
    mode: ExecutionMode = ExecutionMode.LIVE_COMPUTE,
    r27h_precomputed: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validation = validate_user_case(case)
    if not validation["valid"]:
        return {
            "schema_version": _SCHEMA,
            "TASK_ID": _TASK_ID,
            "execution_mode": mode.value,
            "evidence_source": "NONE",
            "validation": validation,
            "delivery_summary": {
                "delivery_status": "USER_CASE_VALIDATION_FAILED",
                "passed": 0,
                "partial": 0,
                "failed": 1,
            },
        }

    if mode == ExecutionMode.LIVE_COMPUTE:
        r27h = run_r27h_candidate_space_extension(case, run_full_mesh=True)
        evidence = "LIVE_R27H_PIPELINE"
    else:
        assert r27h_precomputed is not None
        r27h = r27h_precomputed
        evidence = "R27H_SEALED_FIXTURE_REPLAY"

    design_report = build_full_design_report(case, r27h)
    matrix = acceptance_matrix_strict(mode=mode, case=case, r27h=r27h, design_report=design_report)
    passed = sum(1 for v in matrix.values() if v == "PASS")
    partial = sum(1 for v in matrix.values() if v == "PARTIAL")
    failed = sum(1 for v in matrix.values() if v == "FAIL")
    replay_count = sum(1 for v in matrix.values() if v == "REPLAY")

    if mode == ExecutionMode.LIVE_COMPUTE:
        delivery_status = (
            "V07_LIVE_E2E_COMPLETE" if failed == 0 and passed >= 7 else "V07_LIVE_E2E_INCOMPLETE"
        )
    else:
        delivery_status = "FIXTURE_REPLAY_ONLY_NOT_LIVE_ACCEPTANCE"

    return {
        "schema_version": _SCHEMA,
        "TASK_ID": _TASK_ID,
        "generated_at_utc": datetime.now(tz=UTC).isoformat(),
        "execution_mode": mode.value,
        "evidence_source": evidence,
        "FIXTURE_REPLAY_USED_FOR_LIVE_ACCEPTANCE": mode == ExecutionMode.FIXTURE_REPLAY,
        "acceptance_case_id": case.engineering_case_id,
        "user_case_validation": validation,
        "r27h_search_report": r27h,
        "design_report": design_report,
        "acceptance_function_matrix": matrix,
        "delivery_summary": {
            "passed": passed,
            "partial": partial,
            "failed": failed,
            "replay_labeled": replay_count,
            "delivery_status": delivery_status,
        },
    }


def build_full_design_report(case: EngineeringCase, r27h: dict[str, Any]) -> dict[str, Any]:
    answers = r27h.get("engineering_answers") or {}
    candidates = r27h.get("candidates") or []
    best_prefix = answers.get("best_candidate_id_prefix")
    best = next((c for c in candidates if c.get("candidate_id_prefix") == best_prefix), None)
    mid = ((best or {}).get("loss_scenario_results") or {}).get("mid_band") or {}
    fp = mid.get("full_path_hydraulic_verification") or {}
    cls = (best or {}).get("r27h_classification") or {}
    sens = cls.get("sensitivity") or {}
    max_noz = sens.get("max_nozzle_velocity_audit") or {}
    constraints = (best or {}).get("constraints") or {}
    geom = (best or {}).get("geometry") or {}
    gf = (best or {}).get("geometry_fingerprint") or (best or {}).get("table_row") or {}
    pa = (best or {}).get("phase_a") or {}
    mesh_ev = (best or {}).get("mesh_rating_evidence") or {}
    receipt = (best or {}).get("engineering_delivery_receipt") or {}

    k_summary = {}
    for key in ("low_loss_sensitivity", "mid_band", "high_loss_sensitivity"):
        sc = ((best or {}).get("loss_scenario_results") or {}).get(key) or {}
        fpk = sc.get("full_path_hydraulic_verification") or {}
        k_summary[key] = {
            "full_path_feasible": sc.get("full_path_feasible"),
            "overall_scenario_status": sc.get("overall_scenario_status"),
            "tube_margin_pa": fpk.get("TUBE_FULL_PATH_DP_MARGIN_PA"),
            "shell_margin_pa": fpk.get("SHELL_FULL_PATH_DP_MARGIN_PA"),
        }

    blocked = [
        {
            "candidate_id_prefix": c.get("candidate_id_prefix"),
            "table_row": c.get("table_row"),
            "phase_a_status": (c.get("phase_a") or {}).get("phase_a_status"),
            "outcome_class": c.get("r27h_classification", {}).get("outcome_class")
            or c.get("outcome_class"),
        }
        for c in candidates
        if (c.get("phase_a") or {}).get("phase_a_status")
        not in (
            None,
            "ELIGIBLE_FOR_N1_SCREEN",
        )
        or (c.get("r27h_classification") or {}).get("outcome_class")
        in ("FULL_PATH_NOT_FEASIBLE", "THERMAL_DUTY_NOT_MET", "RATING_INCOMPLETE")
    ]

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
            "shell_inside_diameter_m": geom.get("shell_inside_diameter_m")
            or gf.get("shell_inside_diameter_m"),
            "physical_tube_count": geom.get("physical_tube_count") or pa.get("physical_tube_count"),
            "tube_length_m": geom.get("tube_length_m") or gf.get("tube_length_m"),
            "tube_outer_diameter_m": str(case.candidate_constraints.tube_outer_diameter_m),
            "tube_wall_thickness_m": str(case.candidate_constraints.tube_wall_thickness_m),
            "tube_pitch_m": str(case.candidate_constraints.tube_pitch_m),
            "baffle_count": case.candidate_constraints.baffle_count,
            "baffle_spacing_m": geom.get("baffle_spacing_m") or gf.get("baffle_spacing_m"),
            "nozzles_mid_band": mid.get("selected_nozzles"),
        },
        "thermal_results": {
            "duty_w_at_n4": constraints.get("duty_w_at_finest_mesh"),
            "duty_constraint": constraints.get("duty_constraint"),
            "tube_outlet_k": receipt.get("N4_TUBE_OUTLET_K") if receipt else None,
            "shell_outlet_k": receipt.get("N4_SHELL_OUTLET_K") if receipt else None,
            "mesh_rating_outcome": mesh_ev.get("mesh_rating_outcome"),
            "full_rating_converged": mesh_ev.get("full_rating_converged"),
        },
        "hydraulic_results": {
            "internal_live_postpass": {
                "tube_dp_pa": (best or {}).get("LIVE_TUBE_DP_PA"),
                "shell_dp_pa": (best or {}).get("LIVE_SHELL_DP_PA"),
            },
            "authorized_mid_band_optimized_nozzles": {
                "verification_level": "AUTHORIZED_FULL_PATH_CALCULATOR",
                "tube_total_dp_pa": fp.get("TUBE_FULL_PATH_TOTAL_DP_PA"),
                "shell_total_dp_pa": fp.get("SHELL_FULL_PATH_TOTAL_DP_PA"),
                "tube_margin_pa": fp.get("TUBE_FULL_PATH_DP_MARGIN_PA"),
                "shell_margin_pa": fp.get("SHELL_FULL_PATH_DP_MARGIN_PA"),
                "FULL_PATH_HYDRAULIC_STATUS": fp.get("FULL_PATH_HYDRAULIC_STATUS"),
                "component_rows": fp.get("component_rows"),
            },
            "max_nozzle_velocity_1ms_band_edge_audit": {
                "verification_level": "NOZZLE_BISECT_SIDE_TOTAL_AT_BAND_MAX_DIAMETER",
                "disclosure": ("Not the cooptimized nozzle selection; audit at v≈1.0 m/s only."),
                **max_noz,
            },
        },
        "k_scenario_summary": k_summary,
        "blocked_or_rejected_candidates": blocked,
        "design_conclusion": {
            "outcome_class": cls.get("outcome_class"),
            "disclosure_layers": cls.get("disclosure_layers"),
            "k_authority": "ASSUMPTION_BASED_NOT_ENGINEERING_VALIDATED",
            "mechanical_verification": "NOT_PERFORMED",
            "manufacturing_approval": False,
        },
    }


def verify_independent_input_change(
    base: EngineeringCase, modified: EngineeringCase
) -> dict[str, Any]:
    """Prove modified case inputs change computed screening (Phase A tube regime scan)."""
    from prototypes.v07_general_rating_sizing_mvp.r27h_candidate_space_extension import (
        R27H_EXPERIMENTAL_GEOMETRY_TABLE,
        build_r27h_selection,
        phase_a_r27h_screen,
        _record_for_fingerprint,
    )

    row = R27H_EXPERIMENTAL_GEOMETRY_TABLE[1]
    sel_a = build_r27h_selection(base)
    sel_b = build_r27h_selection(modified)
    rec_a = _record_for_fingerprint(
        sel_a, row["shell_inside_diameter_m"], row["tube_length_m"], row["baffle_spacing_m"]
    )
    rec_b = _record_for_fingerprint(
        sel_b, row["shell_inside_diameter_m"], row["tube_length_m"], row["baffle_spacing_m"]
    )
    assert rec_a and rec_b
    pa_a = phase_a_r27h_screen(case=base, record=rec_a, table_row=row, selection=sel_a)
    pa_b = phase_a_r27h_screen(case=modified, record=rec_b, table_row=row, selection=sel_b)
    scan_a = pa_a.get("tube_regime_inlet_scan") or {}
    scan_b = pa_b.get("tube_regime_inlet_scan") or {}
    changed = pa_a != pa_b or scan_a != scan_b
    return {
        "base_tube_inlet_k": str(base.tube_side.inlet_temperature_k),
        "modified_tube_inlet_k": str(modified.tube_side.inlet_temperature_k),
        "base_target_duty_w": str(base.target_duty_w),
        "modified_target_duty_w": str(modified.target_duty_w),
        "phase_a_status_base": pa_a.get("phase_a_status"),
        "phase_a_status_modified": pa_b.get("phase_a_status"),
        "tube_regime_scan_changed": scan_a != scan_b,
        "input_change_reflected_in_computation": changed,
        "coverage": "Phase A Task174 + tube regime scan on one NEW_EXPERIMENTAL geometry row only.",
    }


def write_v07_delivery_artifacts(report: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "V07_FINAL_LIVE_E2E_DELIVERY.json"
    md_path = output_dir / "V07_DESIGN_REPORT.md"
    json_path.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    dr = report.get("design_report") or {}
    inp = dr.get("input_conditions") or {}
    gen = dr.get("generated_structure") or {}
    hyd = dr.get("hydraulic_results") or {}
    opt = hyd.get("authorized_mid_band_optimized_nozzles") or {}
    audit = hyd.get("max_nozzle_velocity_1ms_band_edge_audit") or {}
    lines = [
        "# V07 final live design report",
        "",
        f"Execution: {report.get('execution_mode')} evidence={report.get('evidence_source')}",
        "",
        "## Input",
        "",
        f"- Tube {inp.get('tube_inlet_k')} K @ {inp.get('tube_mass_flow_kg_s')} kg/s",
        f"- Shell {inp.get('shell_inlet_k')} K @ {inp.get('shell_mass_flow_kg_s')} kg/s",
        f"- Duty ≥ {inp.get('target_duty_w')} W",
        "",
        "## Structure",
        "",
        f"- Shell {gen.get('shell_inside_diameter_m')} m, {gen.get('physical_tube_count')} tubes",
        f"- L={gen.get('tube_length_m')} m, baffles={gen.get('baffle_count')} @ {gen.get('baffle_spacing_m')} m",
        f"- Nozzles (mid_band opt): {gen.get('nozzles_mid_band')}",
        "",
        "## Full path mid_band @ optimized nozzles (authorized)",
        "",
        f"- Tube Δp {opt.get('tube_total_dp_pa')} Pa, margin {opt.get('tube_margin_pa')} Pa",
        f"- Shell Δp {opt.get('shell_total_dp_pa')} Pa, margin {opt.get('shell_margin_pa')} Pa",
        "",
        "## Band-edge v≈1 m/s audit (not optimized selection)",
        "",
        f"- Tube Δp {audit.get('tube_full_path_modeled_dp_pa')} Pa, margin {audit.get('tube_margin_pa')} Pa",
        f"- Shell Δp {audit.get('shell_full_path_modeled_dp_pa')} Pa, margin {audit.get('shell_margin_pa')} Pa",
        "",
        "## K scenarios",
        "",
        json.dumps(dr.get("k_scenario_summary"), indent=2),
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if report.get("r27h_search_report"):
        write_r27h_reports(report["r27h_search_report"], output_dir / "r27h")
    return json_path, md_path


# Backward-compatible aliases
run_v07_end_to_end_acceptance = run_v07_live_e2e
load_v07_acceptance_case = lambda: load_user_case_json(_DEFAULT_LIVE_CASE)
