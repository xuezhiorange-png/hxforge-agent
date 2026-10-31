"""R27A: calculation-first automatic shell-and-tube sizing from design conditions."""

# ruff: noqa: E501

from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from prototypes.v07_general_rating_sizing_mvp.authorized_full_path_hydraulic_calculation import (
    run_authorized_full_path_hydraulic_calculation,
)
from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
    CandidateSelectionOutcome,
    CandidateSelectionRecord,
    enumerate_experimental_rating_candidates,
)
from prototypes.v07_general_rating_sizing_mvp.case_streams import (
    design_conditions_for_report,
    shell_stream_spec,
    tube_stream_spec,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.engineering_hydraulic_path_input_v1 import (
    build_r26g_demonstration_hydraulic_path_input_v1,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_multi_candidate_engineering_sizing import (
    _is_baseline_candidate_b,
    run_experimental_multi_candidate_engineering_sizing,
)

_TASK_ID = "V07_R27A_CALCULATION_FIRST_AUTOMATIC_SIZING"
_SCHEMA = "hxforge.calculation-first-automatic-sizing.v27a"
_SIZING_AUTHORITY = "EXPERIMENTAL_CALCULATION_FIRST_NOT_PRODUCTION_APPROVED"


def _record_map(selection: CandidateSelectionOutcome) -> dict[str, CandidateSelectionRecord]:
    return {row.candidate_id: row for row in selection.records}


def _counterflow_lmtd_k(
    *,
    hot_inlet_k: float,
    hot_outlet_k: float,
    cold_inlet_k: float,
    cold_outlet_k: float,
) -> float | None:
    dt1 = hot_inlet_k - cold_outlet_k
    dt2 = hot_outlet_k - cold_inlet_k
    if dt1 <= 0 or dt2 <= 0:
        return None
    if abs(dt1 - dt2) < 1e-9:
        return dt1
    ratio = dt1 / dt2
    if ratio <= 0:
        return None
    return (dt1 - dt2) / math.log(ratio)


def _effective_overall_u_w_m2_k(
    *,
    duty_w: float | None,
    heat_transfer_area_m2: float | None,
    lmtd_k: float | None,
) -> float | None:
    if duty_w is None or heat_transfer_area_m2 is None or lmtd_k is None:
        return None
    if heat_transfer_area_m2 <= 0 or lmtd_k <= 0:
        return None
    return duty_w / (heat_transfer_area_m2 * lmtd_k)


def _heat_transfer_area_m2(row: dict[str, Any], package: dict[str, Any] | None) -> float | None:
    mesh = (package or {}).get("mesh_convergence") or {}
    results = mesh.get("results") or {}
    for level in (4, 2, 1):
        res = results.get(level)
        meta = getattr(res, "mesh_metadata", None) if res is not None else None
        if meta is not None and meta.task171_total_outside_area_m2:
            return float(meta.task171_total_outside_area_m2)
    proxy = row.get("nominal_tube_outer_area_m2")
    return float(proxy) if proxy is not None else None


def _constraint_summary(row: dict[str, Any], *, target_duty_w: Decimal) -> dict[str, Any]:
    duty = row.get("duty_w_at_finest_mesh")
    duty_ok = duty is not None and float(duty) >= float(target_duty_w)
    tube_margin = row.get("TUBE_DP_MARGIN_PA")
    shell_margin = row.get("SHELL_DP_MARGIN_PA")
    return {
        "target_duty_w": str(target_duty_w),
        "duty_w_at_finest_mesh": duty,
        "duty_constraint": "SATISFIED" if duty_ok else "NOT_SATISFIED_OR_NOT_RATED",
        "tube_dp_margin_pa": tube_margin,
        "shell_dp_margin_pa": shell_margin,
        "tube_dp_constraint": row.get("hydraulic_dp_breakdown", {})
        .get("tube_side", {})
        .get("constraint_status")
        if row.get("hydraulic_dp_breakdown")
        else None,
        "shell_dp_constraint": row.get("hydraulic_dp_breakdown", {})
        .get("shell_side", {})
        .get("constraint_status")
        if row.get("hydraulic_dp_breakdown")
        else None,
        "nominal_experimental_sizing_feasible": row.get("NOMINAL_EXPERIMENTAL_SIZING_FEASIBLE"),
    }


def _sizing_candidate_snapshot(
    *,
    case: EngineeringCase,
    row: dict[str, Any],
    authorized_full_path: dict[str, Any] | None,
) -> dict[str, Any]:
    heat_area = _heat_transfer_area_m2(row, None)
    tube_out = row.get("tube_outlet_temperature_k_n4")
    shell_out = row.get("shell_outlet_temperature_k_n4")
    tube_in = float(tube_stream_spec(case).inlet_temperature_k)
    shell_in = float(shell_stream_spec(case).inlet_temperature_k)
    if tube_in >= shell_in:
        hot_in, hot_out, cold_in, cold_out = tube_in, tube_out, shell_in, shell_out
    else:
        hot_in, hot_out, cold_in, cold_out = shell_in, shell_out, tube_in, tube_out
    lmtd = None
    if hot_out is not None and cold_out is not None:
        lmtd = _counterflow_lmtd_k(
            hot_inlet_k=hot_in,
            hot_outlet_k=float(hot_out),
            cold_inlet_k=cold_in,
            cold_outlet_k=float(cold_out),
        )
    duty = row.get("duty_w_at_finest_mesh")
    u_eff = _effective_overall_u_w_m2_k(
        duty_w=float(duty) if duty is not None else None,
        heat_transfer_area_m2=heat_area,
        lmtd_k=lmtd,
    )
    geom = row.get("candidate_geometry_authority") or {}
    breakdown = row.get("hydraulic_dp_breakdown")
    return {
        "candidate_id": row["candidate_id"],
        "candidate_hash": row.get("candidate_hash"),
        "rating_participation_status": row.get("rating_participation_status"),
        "geometry": {
            "shell_inside_diameter_m": geom.get("shell_inside_diameter_m"),
            "tube_length_m": geom.get("tube_length_m"),
            "baffle_spacing_m": geom.get("baffle_spacing_m"),
            "physical_tube_count": geom.get("physical_tube_count"),
            "tube_pass_count": geom.get("tube_pass_count"),
            "baffle_count": geom.get("baffle_count"),
            "nominal_tube_outer_area_m2": geom.get("nominal_tube_outer_area_m2"),
            "heat_transfer_area_m2_task171": heat_area,
        },
        "thermal_rating": {
            "duty_w": duty,
            "tube_outlet_temperature_k": tube_out,
            "shell_outlet_temperature_k": shell_out,
            "full_rating_converged": row.get("FULL_RATING_CONVERGED"),
            "effective_overall_u_w_m2_k": u_eff,
            "lmtd_k": lmtd,
        },
        "hydraulic_performance": {
            "live_tube_dp_pa": row.get("LIVE_TUBE_DP_PA"),
            "live_shell_dp_pa": row.get("LIVE_SHELL_DP_PA"),
            "tube_dp_margin_pa": row.get("TUBE_DP_MARGIN_PA"),
            "shell_dp_margin_pa": row.get("SHELL_DP_MARGIN_PA"),
            "hydraulic_dp_breakdown": breakdown,
            "authorized_full_path_hydraulic": authorized_full_path,
        },
        "constraints": _constraint_summary(row, target_duty_w=Decimal(str(case.target_duty_w))),
        "elimination_or_incomplete_reason": row.get("elimination_reason"),
        "is_candidate_b_baseline_geometry": row.get("is_candidate_b_baseline_geometry"),
    }


def _recommendation_block(
    multi: dict[str, Any],
    *,
    selection: CandidateSelectionOutcome,
) -> dict[str, Any]:
    ranked = multi.get("ranked_candidates") or []
    best_in_run = multi.get("BEST_EXPERIMENTAL_CANDIDATE_ID")
    not_rated_count = sum(
        1
        for row in multi.get("candidates") or []
        if row.get("rating_participation_status") == "NOT_SELECTED_FOR_RATING"
    )
    return {
        "recommended_candidate_id": best_in_run,
        "recommendation_scope": "BEST_NOMINAL_FEASIBLE_FULLY_RATED_IN_THIS_RUN",
        "global_optimum_disclosure": (
            "Recommendation applies only to candidates fully rated in this run. "
            f"{not_rated_count} enumerated candidate(s) were not selected for rating under "
            "solver_budget.max_candidates_to_rate and are not classified as infeasible."
        ),
        "candidate_space_count": selection.candidate_space_count,
        "task174_ready_count": selection.task174_ready_count,
        "pareto_frontier_candidate_ids": (multi.get("experimental_tradeoff_comparison") or {}).get(
            "AREA_HYDRAULIC_MARGIN_PARETO_FRONTIER_CANDIDATE_IDS"
        ),
        "ranked_feasible_candidate_ids": [row["candidate_id"] for row in ranked],
        "min_area_nominal_candidate_id": multi.get("MIN_AREA_NOMINAL_CANDIDATE_ID"),
    }


def run_calculation_first_automatic_sizing(
    case: EngineeringCase,
    *,
    max_candidates: int | None = None,
    run_full_mesh_hydraulic: bool = True,
    run_authorized_full_path_hydraulic: bool = True,
    precomputed_selection: CandidateSelectionOutcome | None = None,
) -> dict[str, Any]:
    """Design conditions → Task168/174 candidates → rating + hydraulics → sizing report payload."""
    selection = precomputed_selection or enumerate_experimental_rating_candidates(case)
    multi = run_experimental_multi_candidate_engineering_sizing(
        case,
        max_candidates=max_candidates,
        run_full_mesh_hydraulic=run_full_mesh_hydraulic,
        precomputed_selection=selection,
    )
    records = _record_map(selection)
    rate_ids = list(selection.selected_candidate_ids)
    if max_candidates is not None:
        rate_ids = rate_ids[:max_candidates]
    rate_id_set = set(rate_ids)

    authorized_by_id: dict[str, dict[str, Any]] = {}
    if run_authorized_full_path_hydraulic:
        for candidate_id in rate_id_set:
            row = next(
                (r for r in multi["candidates"] if r["candidate_id"] == candidate_id),
                None,
            )
            if row is None or row.get("FULL_RATING_CONVERGED") is not True:
                continue
            record = records.get(candidate_id)
            if record is None or not record.rating_request_ready:
                continue
            path_input = build_r26g_demonstration_hydraulic_path_input_v1(case=case, record=record)
            authorized_by_id[candidate_id] = run_authorized_full_path_hydraulic_calculation(
                case=case,
                path_input=path_input,
                record=record,
                postpass=row.get("live_thermal_state_hydraulic_postpass"),
            )

    sizing_rows = [
        _sizing_candidate_snapshot(
            case=case,
            row=row,
            authorized_full_path=authorized_by_id.get(row["candidate_id"]),
        )
        for row in multi["candidates"]
    ]

    return {
        "schema_version": _SCHEMA,
        "TASK_ID": _TASK_ID,
        "generated_at_utc": datetime.now(tz=UTC).isoformat(),
        "SIZING_TARGET_AUTHORITY": _SIZING_AUTHORITY,
        "PRODUCTION_DESIGN_APPROVED": False,
        "ENGINEERING_SIZING_ELIGIBILITY": "DEMONSTRATION_ONLY_NOT_ENGINEERING_SIZING_ELIGIBLE",
        "user_design_input": design_conditions_for_report(case),
        "manufacturing_search_constraints": case.candidate_constraints.model_dump(mode="json")
        if hasattr(case, "candidate_constraints")
        else None,
        "candidate_generation_summary": {
            "candidate_space_count": selection.candidate_space_count,
            "task174_ready_count": selection.task174_ready_count,
            "selected_for_rating_count": len(rate_id_set),
            "preflight_status": multi.get("CANDIDATE_SPACE_BLOCKER") or "OK",
        },
        "multi_candidate_engineering_run": {
            "TASK_ID": multi.get("TASK_ID"),
            "SCREENED_CANDIDATE_COUNT": multi.get("SCREENED_CANDIDATE_COUNT"),
            "FULLY_RATED_CANDIDATE_COUNT": multi.get("FULLY_RATED_CANDIDATE_COUNT"),
            "NOMINAL_FEASIBLE_COUNT": multi.get("NOMINAL_FEASIBLE_COUNT"),
        },
        "recommendation": _recommendation_block(multi, selection=selection),
        "sizing_candidates": sizing_rows,
        "experimental_tradeoff_comparison": multi.get("experimental_tradeoff_comparison"),
        "engineering_comparison_report": multi.get("engineering_comparison_report"),
        "workflow_status": (
            "SIZING_CALCULATION_COMPLETE"
            if multi.get("FULLY_RATED_CANDIDATE_COUNT", 0) >= 1
            else "SIZING_CALCULATION_PARTIAL"
        ),
        "model_applicability": {
            "fluid": "PURE_ORDINARY_WATER_SINGLE_PHASE",
            "construction": case.exchanger_type,
            "service_envelope": "Experimental MVP; owner review required for production.",
        },
        "engineering_warnings": [
            "Calculation-first sizing is experimental and not production-approved.",
            "Hydraulic breakdown distinguishes computed segments, assumed nozzle/local losses, "
            "and paths not yet modeled — see hydraulic_dp_breakdown per candidate.",
            "Unrated enumerated candidates are not treated as eliminated designs.",
        ],
    }


def render_calculation_first_sizing_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# Calculation-first automatic sizing — {report['TASK_ID']}",
        "",
        f"Generated (UTC): {report['generated_at_utc']}",
        "",
        "## Design input",
        "",
    ]
    dc = report["user_design_input"]
    lines.append(f"- Target duty: **{dc['target_duty_w']} W**")
    lines.append(f"- Max tube Δp: **{dc['max_tube_dp_pa']} Pa**")
    lines.append(f"- Max shell Δp: **{dc['max_shell_dp_pa']} Pa**")
    lines.append("")
    rec = report["recommendation"]
    lines.extend(
        [
            "## Recommendation (scoped to this run)",
            "",
            f"- Recommended candidate: `{rec.get('recommended_candidate_id')}`",
            f"- Scope: **{rec['recommendation_scope']}**",
            f"- Global optimum note: {rec['global_optimum_disclosure']}",
            "",
            "## Candidates",
            "",
        ]
    )
    for row in report["sizing_candidates"]:
        geom = row["geometry"]
        therm = row["thermal_rating"]
        hyd = row["hydraulic_performance"]
        lines.append(f"### `{row['candidate_id']}` ({row['rating_participation_status']})")
        lines.append(
            f"- Shell ID {geom.get('shell_inside_diameter_m')} m, "
            f"L={geom.get('tube_length_m')} m, "
            f"tubes={geom.get('physical_tube_count')}, "
            f"baffle spacing {geom.get('baffle_spacing_m')} m"
        )
        lines.append(
            f"- Area (proxy / Task171): {geom.get('nominal_tube_outer_area_m2')} / "
            f"{geom.get('heat_transfer_area_m2_task171')} m²"
        )
        lines.append(
            f"- Duty: {therm.get('duty_w')} W; "
            f"T_out tube/shell: {therm.get('tube_outlet_temperature_k')} / "
            f"{therm.get('shell_outlet_temperature_k')} K"
        )
        lines.append(
            f"- U_eff: {therm.get('effective_overall_u_w_m2_k')} W/m²K (Q/(A·LMTD) from rated outlets)"
        )
        lines.append(
            f"- Δp tube/shell (live): {hyd.get('live_tube_dp_pa')} / {hyd.get('live_shell_dp_pa')} Pa"
        )
        auth = hyd.get("authorized_full_path_hydraulic") or {}
        lines.append(f"- Authorized full-path hydraulic status: {auth.get('status', 'NOT_RUN')}")
        if row.get("elimination_or_incomplete_reason"):
            lines.append(f"- Note: {row['elimination_or_incomplete_reason']}")
        lines.append("")
    for warn in report.get("engineering_warnings") or []:
        lines.append(f"- ⚠ {warn}")
    return "\n".join(lines) + "\n"


def write_calculation_first_sizing_reports(
    report: dict[str, Any],
    output_dir: Path,
    *,
    basename: str = "R27A_CALCULATION_FIRST_SIZING",
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{basename}.json"
    md_path = output_dir / f"{basename}.md"
    json_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    md_path.write_text(render_calculation_first_sizing_markdown(report), encoding="utf-8")
    return json_path, md_path


def find_middle_reference_record(
    selection: CandidateSelectionOutcome,
) -> CandidateSelectionRecord | None:
    return next(
        (
            r
            for r in selection.records
            if r.rating_request_ready
            and r.tube_length_m == "3.5"
            and r.baffle_spacing_m == "0.7"
            and r.shell_inside_diameter_m == "0.54"
        ),
        None,
    )


def find_candidate_b_record(
    selection: CandidateSelectionOutcome,
) -> CandidateSelectionRecord | None:
    return next(
        (r for r in selection.records if _is_baseline_candidate_b(r) and r.rating_request_ready),
        None,
    )
