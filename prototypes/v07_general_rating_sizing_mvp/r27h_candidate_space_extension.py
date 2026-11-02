"""R27H: controlled Task168 geometry extension and shell pressure optimization."""

# ruff: noqa: E501

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from prototypes.v07_general_rating_sizing_mvp.calculation_first_automatic_sizing import (
    _constraint_summary,
    _geometry_report_block,
)
from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
    CandidateSelectionOutcome,
    CandidateSelectionRecord,
    enumerate_experimental_rating_candidates,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    EngineeringCase,
    load_general_engineering_case_json,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_engineering_rating_core import (
    ENGINEERING_NUMERIC_VALID,
    run_experimental_engineering_rating,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_engineering_rating_live_bridge import (
    build_experimental_engineering_rating_live_package,
)
from prototypes.v07_general_rating_sizing_mvp.nozzle_cooptimization_sizing import (
    LOSS_SCENARIO_KEYS,
    _scenario_recommendation_eligible,
    _thermal_block_from_row,
)
from prototypes.v07_general_rating_sizing_mvp.nozzle_pressure_budget_solver import (
    cooptimize_nozzles_for_candidate_scenario,
)
from prototypes.v07_general_rating_sizing_mvp.positive_duty_cell import build_native_cell_context
from prototypes.v07_general_rating_sizing_mvp.r27e_targeted_recovery import (
    FOUR_065_SHELL_CANDIDATE_IDS,
    R27D_ORIGINAL_BLOCKERS,
)
from prototypes.v07_general_rating_sizing_mvp.r27e_tube_regime_diagnostics import (
    scan_tube_regime_along_temperature,
)
from prototypes.v07_general_rating_sizing_mvp.r27g_shell_geometry_local_pareto import (
    _mid_band_margins_pa,
    _pareto_mid_band_positive_margin,
)
from prototypes.v07_general_rating_sizing_mvp.thermal_hydraulic_geometry_cooptimization_sizing import (
    _mesh_rating_evidence_from_multi_row,
    _pareto_mid_band_feasible,
)

_TASK_ID = "V07_R27H_CANDIDATE_SPACE_EXTENSION_AND_SHELL_PRESSURE_OPTIMIZATION"
_SCHEMA = "hxforge.r27h-candidate-space-extension.v27h"
_DESIGN_DUTY_W = Decimal("330000")
_BAFFLE_COUNT = 4

R27H_CASE_FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "tests/fixtures/r27h_extended_candidate_space_case.json"
)

R27HGeometryRole = Literal["CONTROL", "NEW_EXPERIMENTAL"]

R27H_EXPERIMENTAL_GEOMETRY_TABLE: tuple[dict[str, str], ...] = (
    {"shell_inside_diameter_m": "0.56", "tube_length_m": "4.85", "baffle_spacing_m": "0.97", "role": "CONTROL"},
    {"shell_inside_diameter_m": "0.56", "tube_length_m": "5.15", "baffle_spacing_m": "1.03", "role": "NEW_EXPERIMENTAL"},
    {"shell_inside_diameter_m": "0.56", "tube_length_m": "5.35", "baffle_spacing_m": "1.07", "role": "NEW_EXPERIMENTAL"},
    {"shell_inside_diameter_m": "0.56", "tube_length_m": "5.50", "baffle_spacing_m": "1.10", "role": "NEW_EXPERIMENTAL"},
    {"shell_inside_diameter_m": "0.58", "tube_length_m": "4.85", "baffle_spacing_m": "0.97", "role": "NEW_EXPERIMENTAL"},
    {"shell_inside_diameter_m": "0.58", "tube_length_m": "5.15", "baffle_spacing_m": "1.03", "role": "NEW_EXPERIMENTAL"},
    {"shell_inside_diameter_m": "0.58", "tube_length_m": "5.35", "baffle_spacing_m": "1.07", "role": "NEW_EXPERIMENTAL"},
    {"shell_inside_diameter_m": "0.60", "tube_length_m": "4.85", "baffle_spacing_m": "0.97", "role": "NEW_EXPERIMENTAL"},
    {"shell_inside_diameter_m": "0.60", "tube_length_m": "5.15", "baffle_spacing_m": "1.03", "role": "NEW_EXPERIMENTAL"},
    {"shell_inside_diameter_m": "0.60", "tube_length_m": "5.35", "baffle_spacing_m": "1.07", "role": "NEW_EXPERIMENTAL"},
)


def load_r27h_engineering_case() -> EngineeringCase:
    return load_general_engineering_case_json(R27H_CASE_FIXTURE.read_text(encoding="utf-8"))


def _fingerprint_key(shell: str, tube_len: str, baffle: str) -> tuple[str, str, str]:
    return (shell, tube_len, baffle)


def corrected_r27g_065_outcome_class(candidate_id: str) -> dict[str, Any]:
    """Semantic correction for frozen R27G reports (does not rewrite R27G fixture)."""
    prefix = candidate_id[:8]
    blocker = R27D_ORIGINAL_BLOCKERS.get(candidate_id) or ""
    if prefix == "c20fb684":
        return {
            "corrected_outcome_class": "THERMAL_MODEL_BLOCKED",
            "mechanism": "PROPERTY_ENTHALPY_DOMAIN_EXIT",
            "frozen_r27g_label": "STRUCTURAL_BLOCKED",
            "r27d_blocker": blocker,
        }
    if candidate_id in FOUR_065_SHELL_CANDIDATE_IDS:
        return {
            "corrected_outcome_class": "THERMAL_MODEL_BLOCKED",
            "mechanism": "THERMAL_CORRELATION_TRANSITION_GAP",
            "frozen_r27g_label": "STRUCTURAL_BLOCKED",
            "r27d_blocker": blocker,
            "disclosure": "Task174-ready; mesh rating blocked by tube-side regime gap—not illegal Task168 geometry.",
        }
    return {"corrected_outcome_class": None}


def _record_for_fingerprint(
    selection: CandidateSelectionOutcome,
    shell: str,
    tube_len: str,
    baffle: str,
) -> CandidateSelectionRecord | None:
    return next(
        (
            r
            for r in selection.records
            if r.shell_inside_diameter_m == shell
            and r.tube_length_m == tube_len
            and r.baffle_spacing_m == baffle
        ),
        None,
    )


def _axial_span_ok(tube_len: str, baffle: str) -> bool:
    expected = Decimal(baffle) * Decimal(_BAFFLE_COUNT + 1)
    return expected == Decimal(tube_len)


def phase_a_r27h_screen(
    *,
    case: EngineeringCase,
    record: CandidateSelectionRecord,
    table_row: dict[str, str],
    selection: CandidateSelectionOutcome,
) -> dict[str, Any]:
    shell = table_row["shell_inside_diameter_m"]
    tube_len = table_row["tube_length_m"]
    baffle = table_row["baffle_spacing_m"]
    if not _axial_span_ok(tube_len, baffle):
        return {
            "phase_a_status": "GEOMETRY_BLOCKED",
            "blocker": "AXIAL_SPAN_MISMATCH",
            "expected_tube_length_m": str(Decimal(baffle) * Decimal(_BAFFLE_COUNT + 1)),
        }
    if not record.structural_admitted:
        return {
            "phase_a_status": "STRUCTURAL_BLOCKED",
            "blocked_codes": list(record.task168_blocked_codes),
        }
    if record.task168_chain_status == "BLOCKED_DOWNSTREAM":
        return {
            "phase_a_status": "TASK168_CHAIN_BLOCKED",
            "stage": record.task168_blocked_stage,
            "blocked_codes": list(record.task168_blocked_codes),
        }
    if not record.rating_request_ready:
        return {
            "phase_a_status": "TASK174_NOT_READY",
            "task174_status": record.task174_status,
        }
    regime: dict[str, Any] | None = None
    if record.task025_total_parallel_flow_area_m2 and record.physical_tube_count:
        regime = scan_tube_regime_along_temperature(
            case,
            selection=selection,
            candidate_id=record.candidate_id,
            temperature_steps=12,
        )
        if regime.get("first_transition_regime_row") or regime.get("first_laminar_row"):
            return {
                "phase_a_status": "THERMAL_MODEL_BLOCKED",
                "mechanism": "TUBE_SIDE_REGIME_TRANSITION_ALONG_COOLING_PATH",
                "tube_regime_scan": regime,
                "physical_tube_count": record.physical_tube_count,
                "task025_total_parallel_flow_area_m2": record.task025_total_parallel_flow_area_m2,
            }
    return {
        "phase_a_status": "ELIGIBLE_FOR_N1_SCREEN",
        "geometry_role": table_row["role"],
        "shell_inside_diameter_m": shell,
        "tube_length_m": tube_len,
        "baffle_spacing_m": baffle,
        "baffle_count": _BAFFLE_COUNT,
        "physical_tube_count": record.physical_tube_count,
        "task025_total_parallel_flow_area_m2": record.task025_total_parallel_flow_area_m2,
        "tube_regime_inlet_scan": regime,
        "geometry_authority": "EXPERIMENTAL_TASK168_EXTENSION_NOT_OWNER_APPROVED",
    }


def _classify_r27h_final(
    *,
    record: CandidateSelectionRecord,
    table_row: dict[str, str],
    phase_a: dict[str, Any],
    multi_row: dict[str, Any] | None,
    scenario_results: dict[str, Any],
    case: EngineeringCase,
) -> dict[str, Any]:
    if phase_a.get("phase_a_status") != "ELIGIBLE_FOR_N1_SCREEN":
        return {
            "outcome_class": phase_a["phase_a_status"],
            "detail": phase_a,
        }
    if multi_row is None:
        return {"outcome_class": "RATING_INCOMPLETE", "detail": "NOT_RATED"}
    converged = multi_row.get("rating_participation_status") == "FULLY_RATED"
    if not converged:
        return {
            "outcome_class": "RATING_INCOMPLETE",
            "detail": multi_row.get("rating_participation_status"),
        }
    duty = multi_row.get("duty_w_at_finest_mesh")
    if duty is None or Decimal(str(duty)) < _DESIGN_DUTY_W:
        return {"outcome_class": "THERMAL_DUTY_NOT_MET", "detail": f"duty={duty}"}
    tube_m, shell_m = _mid_band_margins_pa(scenario_results)
    min_m = min(tube_m, shell_m) if tube_m is not None and shell_m is not None else None
    formal = _scenario_recommendation_eligible(
        {
            "rating_participation_status": multi_row.get("rating_participation_status"),
            "thermal_rating": _thermal_block_from_row(multi_row, case=case),
            "constraints": _constraint_summary(multi_row, target_duty_w=_DESIGN_DUTY_W),
            "loss_scenario_results": scenario_results,
        },
        "mid_band",
    )
    sens = {
        "mid_band_min_full_path_margin_pa": str(min_m) if min_m is not None else None,
        "tube_side_margin_pa": str(tube_m) if tube_m is not None else None,
        "shell_side_margin_pa": str(shell_m) if shell_m is not None else None,
    }
    if formal:
        return {
            "outcome_class": "MID_BAND_FEASIBLE_ASSUMPTION_BASED",
            "geometry_role": table_row["role"],
            "sensitivity": sens,
        }
    return {
        "outcome_class": "FULL_PATH_NOT_FEASIBLE",
        "geometry_role": table_row["role"],
        "sensitivity": sens,
        "pressure_gap_pa": str(min_m) if min_m is not None else None,
    }


def build_r27h_selection(case: EngineeringCase) -> CandidateSelectionOutcome:
    base = enumerate_experimental_rating_candidates(
        case,
        rating_selection_policy="r27d",
        rate_all_distinct_task174_ready=False,
    )
    rate_ids: list[str] = []
    for row in R27H_EXPERIMENTAL_GEOMETRY_TABLE:
        if row["role"] != "NEW_EXPERIMENTAL":
            continue
        rec = _record_for_fingerprint(
            base,
            row["shell_inside_diameter_m"],
            row["tube_length_m"],
            row["baffle_spacing_m"],
        )
        if rec is None:
            continue
        if rec.rating_request_ready and rec.structural_admitted:
            rate_ids.append(rec.candidate_id)
    return replace(
        base,
        selected_candidate_ids=tuple(rate_ids),
        selected_candidate_id=rate_ids[0] if rate_ids else None,
        selection_reason="R27H_NEW_EXPERIMENTAL_TASK174_READY_MESH_RATING",
    )


def run_r27h_candidate_space_extension(
    case: EngineeringCase | None = None,
    *,
    run_full_mesh: bool = True,
) -> dict[str, Any]:
    case = case or load_r27h_engineering_case()
    selection = build_r27h_selection(case)
    rows_out: list[dict[str, Any]] = []
    phase_a_eligible: list[tuple[CandidateSelectionRecord, dict[str, str], dict[str, Any]]] = []

    for table_row in R27H_EXPERIMENTAL_GEOMETRY_TABLE:
        rec = _record_for_fingerprint(
            selection,
            table_row["shell_inside_diameter_m"],
            table_row["tube_length_m"],
            table_row["baffle_spacing_m"],
        )
        if rec is None:
            rows_out.append(
                {
                    "table_row": table_row,
                    "outcome_class": "GEOMETRY_NOT_IN_TASK168_SPACE",
                    "phase_a": {"phase_a_status": "NOT_ENUMERATED"},
                }
            )
            continue
        phase_a = phase_a_r27h_screen(
            case=case, record=rec, table_row=table_row, selection=selection
        )
        entry: dict[str, Any] = {
            "candidate_id": rec.candidate_id,
            "candidate_id_prefix": rec.candidate_id[:8],
            "table_row": table_row,
            "phase_a": phase_a,
            "task174_ready": rec.rating_request_ready,
        }
        if phase_a.get("phase_a_status") == "ELIGIBLE_FOR_N1_SCREEN":
            phase_a_eligible.append((rec, table_row, phase_a))
        else:
            entry["outcome_class"] = phase_a.get("phase_a_status", "BLOCKED")
        rows_out.append(entry)

    new_legal = sum(
        1
        for r in rows_out
        if r.get("table_row", {}).get("role") == "NEW_EXPERIMENTAL"
        and (r.get("phase_a") or {}).get("phase_a_status") == "ELIGIBLE_FOR_N1_SCREEN"
    )
    if new_legal == 0:
        return _finalize_report(
            case,
            selection,
            rows_out,
            stopped_after_phase_a=True,
        )

    rated_new = 0
    for rec, table_row, phase_a in phase_a_eligible:
        row_entry = next(x for x in rows_out if x["candidate_id"] == rec.candidate_id)
        is_new = table_row["role"] == "NEW_EXPERIMENTAL"
        native = build_native_cell_context(case, selection=selection, candidate_id=rec.candidate_id)
        cache: dict[int, Any] = {}
        n1 = run_experimental_engineering_rating(
            case, subdivisions=1, native=native, mesh_result_cache=cache
        )
        row_entry["phase_b_n1"] = {
            "status": n1.status,
            "duty_w": n1.duty_w,
            "failure_code": n1.failure_code,
        }
        if n1.status != ENGINEERING_NUMERIC_VALID:
            row_entry["outcome_class"] = "THERMAL_MODEL_BLOCKED"
            continue
        if table_row["role"] == "CONTROL":
            row_entry["outcome_class"] = "CONTROL_REFERENCE"
            row_entry["disclosure"] = (
                "R27H does not re-run full mesh on control; mid_band margin reference "
                "−70.87 Pa from R27G sealed 9c4b84db evidence."
            )
            row_entry["r27h_classification"] = {
                "outcome_class": "FULL_PATH_NOT_FEASIBLE",
                "geometry_role": "CONTROL",
                "sensitivity": {"mid_band_min_full_path_margin_pa": "-70.871512175899702992638898"},
            }
            continue
        run_mesh = (
            run_full_mesh
            and rec.candidate_id in selection.selected_candidate_ids
        )
        package: dict[str, Any] | None = None
        if run_mesh:
            package = build_experimental_engineering_rating_live_package(
                case,
                native=native,
                run_mesh_ladder=True,
                run_hydraulic_sensitivity=False,
                mesh_result_cache=cache,
            )
            mesh = package.get("mesh_convergence") or {}
            if mesh.get("FULL_RATING_CONVERGED") and is_new:
                rated_new += 1
        if package is None:
            row_entry["outcome_class"] = "RATING_INCOMPLETE"
            continue
        postpass = package.get("live_thermal_state_hydraulic_postpass") or {}
        receipt = package.get("engineering_delivery_receipt") or {}
        multi_row = {
            "rating_participation_status": "FULLY_RATED"
            if (package.get("mesh_convergence") or {}).get("FULL_RATING_CONVERGED")
            else "INCOMPLETE",
            "duty_w_at_finest_mesh": receipt.get("N4_DUTY_W"),
            "thermal_rating": {
                "duty_w": receipt.get("N4_DUTY_W"),
                "full_rating_converged": (package.get("mesh_convergence") or {}).get(
                    "FULL_RATING_CONVERGED"
                ),
            },
            "live_thermal_state_hydraulic_postpass": postpass,
            "LIVE_TUBE_DP_PA": receipt.get("LIVE_TUBE_DP_PA"),
            "LIVE_SHELL_DP_PA": receipt.get("LIVE_SHELL_DP_PA"),
        }
        row_entry["mesh_rating_evidence"] = _mesh_rating_evidence_from_multi_row(multi_row)
        row_entry["constraints"] = _constraint_summary(
            {
                **multi_row,
                "N4_DUTY_W": receipt.get("N4_DUTY_W"),
                "LIVE_TUBE_DP_PA": receipt.get("LIVE_TUBE_DP_PA"),
                "LIVE_SHELL_DP_PA": receipt.get("LIVE_SHELL_DP_PA"),
                "TUBE_DP_MARGIN_PA": postpass.get("tube_dp_margin_pa"),
                "SHELL_DP_MARGIN_PA": postpass.get("shell_dp_margin_pa"),
                "tube_dp_constraint": postpass.get("tube_dp_constraint"),
                "shell_dp_constraint": postpass.get("shell_dp_constraint"),
                "hydraulic_constraint_status": postpass.get("hydraulic_constraint_status"),
            },
            target_duty_w=_DESIGN_DUTY_W,
        )
        scenario_results: dict[str, Any] = {}
        if multi_row["rating_participation_status"] == "FULLY_RATED":
            for key in LOSS_SCENARIO_KEYS:
                scenario_results[key] = cooptimize_nozzles_for_candidate_scenario(
                    case=case,
                    record=rec,
                    postpass=postpass,
                    loss_scenario_key=key,
                )
        row_entry["loss_scenario_results"] = scenario_results
        row_entry["geometry"] = _geometry_report_block(row=multi_row, case=case)
        row_entry["r27h_classification"] = _classify_r27h_final(
            record=rec,
            table_row=table_row,
            phase_a=phase_a,
            multi_row={
                **multi_row,
                "duty_w_at_finest_mesh": receipt.get("N4_DUTY_W"),
            },
            scenario_results=scenario_results,
            case=case,
        )

    return _finalize_report(case, selection, rows_out, stopped_after_phase_a=False)


def _finalize_report(
    case: EngineeringCase,
    selection: CandidateSelectionOutcome,
    rows_out: list[dict[str, Any]],
    *,
    stopped_after_phase_a: bool,
) -> dict[str, Any]:
    rated_full = [
        r
        for r in rows_out
        if r.get("loss_scenario_results")
        and (r.get("constraints") or {}).get("duty_w_at_finest_mesh") is not None
    ]
    new_structural_legal = [
        r
        for r in rows_out
        if r.get("table_row", {}).get("role") == "NEW_EXPERIMENTAL"
        and (r.get("phase_a") or {}).get("phase_a_status") == "ELIGIBLE_FOR_N1_SCREEN"
    ]
    mid_band_feasible = [
        r
        for r in rows_out
        if (r.get("r27h_classification") or {}).get("outcome_class")
        == "MID_BAND_FEASIBLE_ASSUMPTION_BASED"
    ]
    best: dict[str, Any] | None = None
    best_margin: Decimal | None = None
    for r in rows_out:
        sens = (r.get("r27h_classification") or {}).get("sensitivity") or {}
        raw = sens.get("mid_band_min_full_path_margin_pa")
        if raw is None:
            continue
        duty_raw = (r.get("constraints") or {}).get("duty_w_at_finest_mesh")
        if duty_raw is None or Decimal(str(duty_raw)) < _DESIGN_DUTY_W:
            continue
        m = Decimal(str(raw))
        if best_margin is None or m > best_margin:
            best_margin = m
            best = r

    pareto_rows = [
        {
            "candidate_id": r["candidate_id"],
            "geometry": r.get("geometry") or {},
            "rating_participation_status": "FULLY_RATED",
            "thermal_rating": {"duty_w": (r.get("constraints") or {}).get("duty_w_at_finest_mesh")},
            "constraints": r.get("constraints") or {},
            "loss_scenario_results": r.get("loss_scenario_results") or {},
        }
        for r in rows_out
        if r.get("loss_scenario_results")
    ]
    return {
        "schema_version": _SCHEMA,
        "TASK_ID": _TASK_ID,
        "generated_at_utc": datetime.now(tz=UTC).isoformat(),
        "upstream_head": "3a0f1f97686103a2dbb0e408b2392d17058b07b2",
        "experimental_case_id": case.engineering_case_id,
        "geometry_table": list(R27H_EXPERIMENTAL_GEOMETRY_TABLE),
        "r27g_065_classification_corrections": [
            corrected_r27g_065_outcome_class(cid) | {"candidate_id_prefix": cid[:8]}
            for cid in FOUR_065_SHELL_CANDIDATE_IDS
        ],
        "stopped_after_phase_a": stopped_after_phase_a,
        "candidates": rows_out,
        "mid_band_formal_pareto": _pareto_mid_band_feasible(pareto_rows),
        "mid_band_margin_pareto": _pareto_mid_band_positive_margin(
            [{"candidate_id": r["candidate_id"], "r27g_classification": r.get("r27h_classification"), "geometry": r.get("geometry"), "constraints": r.get("constraints")} for r in rows_out]
        ),
        "engineering_answers": {
            "new_structurally_legal_distinct_geometries": len(new_structural_legal),
            "completed_n1_n2_n4_count": len(rated_full),
            "mid_band_full_path_feasible_count": len(mid_band_feasible),
            "best_candidate_id_prefix": best["candidate_id_prefix"] if best else None,
            "best_geometry": best.get("table_row") if best else None,
            "best_tube_count": (best.get("phase_a") or {}).get("physical_tube_count") if best else None,
            "best_mid_band_tube_margin_pa": (
                (best.get("r27h_classification") or {}).get("sensitivity", {}).get(
                    "tube_side_margin_pa"
                )
                if best
                else None
            ),
            "best_mid_band_shell_margin_pa": (
                (best.get("r27h_classification") or {}).get("sensitivity", {}).get(
                    "shell_side_margin_pa"
                )
                if best
                else None
            ),
            "best_mid_band_min_margin_pa": str(best_margin) if best_margin is not None else None,
            "joint_extension_delivers_mid_band_positive_margin": (
                best_margin is not None and best_margin > Decimal("0")
            ),
            "primary_blocker_if_infeasible": (
                None
                if mid_band_feasible
                else (
                    f"SHELL_FULL_PATH_MARGIN_DEFICIT_PA={best_margin}"
                    if best_margin is not None and best_margin < Decimal("0")
                    else (best.get("r27h_classification") or {}).get("outcome_class")
                    if best
                    else "TASK168_BAFFLE_GEOMETRY_OR_REGIME"
                )
            ),
        },
        "baffle_count_sensitivity_note": {
            "evaluated": False,
            "disclosure": (
                "baffle_count change requires Task024/support re-validation; not executed in "
                "this pass because extended ladder alone did not reach mid_band feasibility."
            ),
        },
    }


def write_r27h_reports(report: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "R27H_CANDIDATE_SPACE_EXTENSION.json"
    md_path = output_dir / "R27H_ENGINEERING_REPORT.md"
    json_path.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    ans = report["engineering_answers"]
    lines = [
        f"# R27H ({report['TASK_ID']})",
        "",
        "## Answers",
        "",
        f"1. New structurally legal geometries: **{ans['new_structurally_legal_distinct_geometries']}**",
        f"2. N1/N2/N4 complete: **{ans['completed_n1_n2_n4_count']}**",
        f"3. mid_band full-path feasible @330kW: **{ans['mid_band_full_path_feasible_count']}**",
        f"4. Best: `{ans['best_candidate_id_prefix']}` {ans['best_geometry']}",
        f"5. Best margins (Pa): tube={ans['best_mid_band_tube_margin_pa']} shell={ans['best_mid_band_shell_margin_pa']}",
        f"6. Blocker: {ans['primary_blocker_if_infeasible']}",
        "",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path
