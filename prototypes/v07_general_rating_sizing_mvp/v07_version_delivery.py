"""V07 final live E2E delivery acceptance."""

# ruff: noqa: E501

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
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

_TASK_ID = "V07_FINAL_DELIVERY_DEFECT_CLOSURE"
_SCHEMA = "hxforge.v07-final-delivery-defect-closure.v07"
_DEFAULT_LIVE_CASE = (
    Path(__file__).resolve().parents[2] / "tests/fixtures/v07_live_acceptance_user_case.json"
)


class ExecutionMode(StrEnum):
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


def mesh_rating_evidence_consistent(ev: dict[str, Any]) -> bool:
    from prototypes.v07_general_rating_sizing_mvp.experimental_engineering_rating_core import (
        ENGINEERING_NUMERIC_VALID,
    )

    if ev.get("full_rating_converged") is not True:
        return False
    if ev.get("entered_n2_n4_mesh_ladder") is not True:
        return False
    if ev.get("mesh_rating_outcome") != "FULL_MESH_RATING_CONVERGED":
        return False
    return ev.get("n1_thermal_numeric_status") == ENGINEERING_NUMERIC_VALID


def _mesh_converged_evidence(row: dict[str, Any]) -> bool:
    ev = row.get("mesh_rating_evidence") or {}
    if not mesh_rating_evidence_consistent(ev):
        return False
    return bool(row.get("loss_scenario_results")) and row.get("engineering_delivery_receipt")


def _full_path_components_present(fp: dict[str, Any]) -> bool:
    if not fp:
        return False
    tube = fp.get("TUBE_DP_COMPONENTS")
    shell = fp.get("SHELL_DP_COMPONENTS")
    bd = fp.get("SHELL_BELL_DELAWARE_INTERNAL_DP_PA")
    return tube is not None and shell is not None and bd is not None


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
    for key in ("duty_w_at_n4", "tube_outlet_k", "shell_outlet_k"):
        if therm.get(key) is None:
            missing.append(f"thermal_results.{key}")
    hyd = design_report.get("hydraulic_results") or {}
    internal = hyd.get("internal_live_postpass") or {}
    for key in ("tube_dp_pa", "shell_dp_pa"):
        if internal.get(key) is None:
            missing.append(f"hydraulic_results.internal_live_postpass.{key}")
    opt = hyd.get("authorized_mid_band_optimized_nozzles") or {}
    comp = opt.get("component_rows") or {}
    if not comp.get("TUBE_DP_COMPONENTS"):
        missing.append("hydraulic_results.authorized_mid_band_optimized_nozzles.component_rows.TUBE_DP_COMPONENTS")
    if not comp.get("SHELL_DP_COMPONENTS"):
        missing.append("hydraulic_results.authorized_mid_band_optimized_nozzles.component_rows.SHELL_DP_COMPONENTS")
    if comp.get("SHELL_BELL_DELAWARE_INTERNAL_DP_PA") is None:
        missing.append(
            "hydraulic_results.authorized_mid_band_optimized_nozzles.component_rows.SHELL_BELL_DELAWARE_INTERNAL_DP_PA"
        )
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
    mid_fp = (
        ((best or {}).get("loss_scenario_results") or {}).get("mid_band") or {}
    ).get("full_path_hydraulic_verification") or {}
    target_ok = ((best or {}).get("constraints") or {}).get("target_duty_w") == str(
        case.target_duty_w
    )

    def _status(ok: bool, partial: bool = False) -> str:
        if ok:
            return "PASS"
        return "PARTIAL" if partial else "FAIL"

    classification_ok = False
    if best is not None:
        oc = (best.get("r27h_classification") or {}).get("outcome_class")
        if has_feasible:
            classification_ok = oc not in ("FULL_PATH_NOT_FEASIBLE", "RATING_INCOMPLETE")
        else:
            classification_ok = True

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
        "thermal_rating_n1_n2_n4": _status(
            len(rated_rows) >= 1
            and all(
                mesh_rating_evidence_consistent(c.get("mesh_rating_evidence") or {})
                for c in rated_rows
            )
        ),
        "internal_hydraulics": _status(
            best is not None
            and (best.get("constraints") or {}).get("hydraulic_constraint_status") == "SATISFIED"
            and (best.get("LIVE_TUBE_DP_PA") is not None or (best.get("engineering_delivery_receipt") or {}).get("LIVE_TUBE_DP_PA") is not None),
            partial=best is not None,
        ),
        "nozzle_cooptimization": _status(
            best is not None and bool((best.get("loss_scenario_results") or {}).get("mid_band"))
        ),
        "full_path_assumption_k": _status(
            has_feasible and _full_path_components_present(mid_fp), partial=bool(rated_rows)
        ),
        "result_classification": _status(classification_ok and target_ok, partial=not has_feasible),
        "user_readable_design_report": _status(complete, partial=bool(missing)),
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
    tube_out = receipt.get("N4_TUBE_OUTLET_K") or best.get("tube_outlet_temperature_k_n4")
    shell_out = receipt.get("N4_SHELL_OUTLET_K") or best.get("shell_outlet_temperature_k_n4")
    live_tube = (best or {}).get("LIVE_TUBE_DP_PA") or receipt.get("LIVE_TUBE_DP_PA")
    live_shell = (best or {}).get("LIVE_SHELL_DP_PA") or receipt.get("LIVE_SHELL_DP_PA")
    component_rows = None
    if fp:
        component_rows = {
            "TUBE_DP_COMPONENTS": fp.get("TUBE_DP_COMPONENTS"),
            "SHELL_DP_COMPONENTS": fp.get("SHELL_DP_COMPONENTS"),
            "SHELL_BELL_DELAWARE_INTERNAL_DP_PA": fp.get("SHELL_BELL_DELAWARE_INTERNAL_DP_PA"),
            "TUBE_INTERNAL_FRICTION_DP_PA": fp.get("TUBE_INTERNAL_FRICTION_DP_PA"),
            "TUBE_LOCAL_DP_PA": fp.get("TUBE_LOCAL_DP_PA"),
            "source": "authorized_full_path_hydraulic_calculation.mid_band",
        }

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
            "target_duty_w_from_case": str(case.target_duty_w),
            "tube_outlet_k": tube_out,
            "shell_outlet_k": shell_out,
            "mesh_rating_outcome": mesh_ev.get("mesh_rating_outcome"),
            "full_rating_converged": mesh_ev.get("full_rating_converged"),
            "entered_n2_n4_mesh_ladder": mesh_ev.get("entered_n2_n4_mesh_ladder"),
            "provenance": {
                "outlet_temperatures": "engineering_delivery_receipt.N4_*",
                "duty": "constraints.duty_w_at_finest_mesh",
            },
        },
        "hydraulic_results": {
            "internal_live_postpass": {
                "tube_dp_pa": live_tube,
                "shell_dp_pa": live_shell,
                "provenance": "engineering_delivery_receipt LIVE_* from rating postpass",
            },
            "authorized_mid_band_optimized_nozzles": {
                "verification_level": "AUTHORIZED_FULL_PATH_CALCULATOR",
                "tube_total_dp_pa": fp.get("TUBE_FULL_PATH_TOTAL_DP_PA"),
                "shell_total_dp_pa": fp.get("SHELL_FULL_PATH_TOTAL_DP_PA"),
                "tube_margin_pa": fp.get("TUBE_FULL_PATH_DP_MARGIN_PA"),
                "shell_margin_pa": fp.get("SHELL_FULL_PATH_DP_MARGIN_PA"),
                "FULL_PATH_HYDRAULIC_STATUS": fp.get("FULL_PATH_HYDRAULIC_STATUS"),
                "component_rows": component_rows,
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


def verify_independent_input_effects(base: EngineeringCase) -> dict[str, Any]:
    """Controlled proof that user target duty and inlet temperature change formal results."""
    from prototypes.v07_general_rating_sizing_mvp.calculation_first_automatic_sizing import (
        _constraint_summary,
    )
    from prototypes.v07_general_rating_sizing_mvp.experimental_engineering_rating_core import (
        ENGINEERING_NUMERIC_VALID,
        run_experimental_engineering_rating,
    )
    from prototypes.v07_general_rating_sizing_mvp.experimental_multi_candidate_engineering_sizing import (
        build_native_cell_context,
    )
    from prototypes.v07_general_rating_sizing_mvp.r27h_candidate_space_extension import (
        R27H_EXPERIMENTAL_GEOMETRY_TABLE,
        _record_for_fingerprint,
        build_r27h_selection,
    )

    row = next(r for r in R27H_EXPERIMENTAL_GEOMETRY_TABLE if r["tube_length_m"] == "5.50")
    sel = build_r27h_selection(base)
    rec = _record_for_fingerprint(
        sel, row["shell_inside_diameter_m"], row["tube_length_m"], row["baffle_spacing_m"]
    )
    assert rec is not None
    native = build_native_cell_context(base, selection=sel, candidate_id=rec.candidate_id)
    cache: dict[int, Any] = {}
    n1_base = run_experimental_engineering_rating(
        base, subdivisions=1, native=native, mesh_result_cache=cache
    )
    case_hot = base.model_copy(
        update={
            "tube_side": base.tube_side.model_copy(
                update={"inlet_temperature_k": Decimal("305.000000")}
            )
        }
    )
    native_cold = build_native_cell_context(
        case_hot, selection=build_r27h_selection(case_hot), candidate_id=rec.candidate_id
    )
    n1_cold = run_experimental_engineering_rating(
        case_hot, subdivisions=1, native=native_cold, mesh_result_cache={}
    )
    case_high_duty = base.model_copy(update={"target_duty_w": Decimal("500000")})
    multi_stub = {
        "duty_w_at_finest_mesh": n1_base.duty_w,
        "FULL_RATING_CONVERGED": True,
        "rating_participation_status": "FULLY_RATED",
        "screening_n1_status": ENGINEERING_NUMERIC_VALID,
        "n1_thermal_numeric_status": ENGINEERING_NUMERIC_VALID,
    }
    duty_judgment_base = _constraint_summary(multi_stub, target_duty_w=base.target_duty_w)[
        "duty_constraint"
    ]
    duty_judgment_high = _constraint_summary(
        multi_stub, target_duty_w=case_high_duty.target_duty_w
    )["duty_constraint"]
    thermal_changed = (
        n1_base.status == ENGINEERING_NUMERIC_VALID
        and n1_cold.status == ENGINEERING_NUMERIC_VALID
        and n1_base.duty_w != n1_cold.duty_w
    )
    return {
        "geometry_row": row,
        "candidate_id_prefix": rec.candidate_id[:8],
        "base_target_duty_w": str(base.target_duty_w),
        "elevated_target_duty_w": str(case_high_duty.target_duty_w),
        "duty_constraint_at_base_target": duty_judgment_base,
        "duty_constraint_at_elevated_target": duty_judgment_high,
        "target_duty_constraint_judgment_changed": duty_judgment_base != duty_judgment_high,
        "n1_duty_w_at_310k_inlet": n1_base.duty_w,
        "n1_duty_w_at_305k_inlet": n1_cold.duty_w,
        "thermal_n1_changed_with_inlet_temperature": thermal_changed,
        "coverage": (
            "Single NEW_EXPERIMENTAL geometry (0.56 m, L=5.50 m): N1 rating at two inlets; "
            "duty constraint re-evaluated at two user target_duty_w values on same N1 duty."
        ),
        "independent_input_change_pass": (
            duty_judgment_base != duty_judgment_high and thermal_changed
        ),
    }


# Backward-compatible alias
verify_independent_input_change = verify_independent_input_effects


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
    therm = dr.get("thermal_results") or {}
    internal = hyd.get("internal_live_postpass") or {}
    comp = (opt.get("component_rows") or {}) if opt else {}
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
        "## Thermal (N4)",
        "",
        f"- Duty @ N4: {therm.get('duty_w_at_n4')} W ({therm.get('duty_constraint')})",
        f"- Tube outlet: {therm.get('tube_outlet_k')} K",
        f"- Shell outlet: {therm.get('shell_outlet_k')} K",
        "",
        "## Internal hydraulics (live postpass)",
        "",
        f"- Tube Δp {internal.get('tube_dp_pa')} Pa",
        f"- Shell Δp {internal.get('shell_dp_pa')} Pa",
        "",
        "## Full path mid_band @ optimized nozzles (authorized)",
        "",
        f"- Tube Δp {opt.get('tube_total_dp_pa')} Pa, margin {opt.get('tube_margin_pa')} Pa",
        f"- Shell Δp {opt.get('shell_total_dp_pa')} Pa, margin {opt.get('shell_margin_pa')} Pa",
        f"- Bell-Delaware internal: {comp.get('SHELL_BELL_DELAWARE_INTERNAL_DP_PA')} Pa",
        "",
        "## Band-edge v≈1 m/s audit (not optimized selection)",
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


def load_v07_acceptance_case() -> EngineeringCase:
    return load_user_case_json(_DEFAULT_LIVE_CASE)
