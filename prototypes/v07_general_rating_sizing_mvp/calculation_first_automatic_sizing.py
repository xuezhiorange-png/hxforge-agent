"""R27A: calculation-first automatic shell-and-tube sizing from design conditions."""

# ruff: noqa: E501

from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from hexagent.properties.base import FluidIdentifier
from hexagent.properties.coolprop_provider import CoolPropProvider
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

_TASK_ID = "V07_R27A_CALCULATION_REPORT_INTEGRITY"
_SCHEMA = "hxforge.calculation-first-automatic-sizing.v27a-integrity"
_SIZING_AUTHORITY = "EXPERIMENTAL_CALCULATION_FIRST_NOT_PRODUCTION_APPROVED"

NOZZLE_VELOCITY_DESIGN_RULE: dict[str, Any] = {
    "rule_id": "R27A-PRELIMINARY-NOZZLE-VELOCITY-BAND",
    "source_nature": "CONFIGURABLE_PRELIMINARY_DESIGN_ASSUMPTION",
    "velocity_m_s_min": 1.0,
    "velocity_m_s_max": 3.0,
    "disclosure": (
        "Preliminary nozzle inside diameter from m/(rho*A) with a configurable velocity band; "
        "not an owner-approved project specification."
    ),
}

CandidateFeasibilityClass = Literal[
    "NOT_RATED_THIS_RUN",
    "PARTIAL_RATING_ONLY",
    "THERMAL_AND_PARTIAL_HYDRAULIC_NOMINAL",
    "DEMONSTRATION_FULL_PATH_COMPARISON_ONLY",
    "NOT_EVALUATED",
]


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


def _counterflow_equivalent_u_w_m2_k(
    *,
    duty_w: float | None,
    area_m2: float | None,
    lmtd_k: float | None,
) -> float | None:
    if duty_w is None or area_m2 is None or lmtd_k is None:
        return None
    if area_m2 <= 0 or lmtd_k <= 0:
        return None
    return duty_w / (area_m2 * lmtd_k)


def _geometry_report_block(
    *,
    row: dict[str, Any],
    case: EngineeringCase,
) -> dict[str, Any]:
    authority = row.get("candidate_geometry_authority") or {}
    constraints = case.candidate_constraints
    task171_area = row.get("task171_total_outside_area_m2")
    return {
        "geometry_authority": authority.get(
            "geometry_authority", "TASK168_TASK021_SELECTION_RECORD"
        ),
        "shell_inside_diameter_m": authority.get("shell_inside_diameter_m"),
        "physical_tube_count": authority.get("physical_tube_count"),
        "tube_length_m": authority.get("tube_length_m"),
        "baffle_spacing_m": authority.get("baffle_spacing_m"),
        "tube_pass_count": {
            "value": constraints.tube_pass_count,
            "authority": "CASE_MANUFACTURING_SEARCH_CONSTRAINT",
        },
        "baffle_count": {
            "value": constraints.baffle_count,
            "authority": "CASE_MANUFACTURING_SEARCH_CONSTRAINT",
        },
        "nominal_tube_outer_area_proxy_m2": authority.get("nominal_tube_outer_area_m2"),
        "task171_rated_outside_area_m2": task171_area,
        "task171_rated_outside_area_status": (
            "FROM_FULL_MESH_RATING"
            if task171_area is not None
            else "NOT_AVAILABLE_UNTIL_FULL_RATING"
        ),
    }


def _constraint_summary(row: dict[str, Any], *, target_duty_w: Decimal) -> dict[str, Any]:
    full_converged = row.get("FULL_RATING_CONVERGED") is True
    duty = row.get("duty_w_at_finest_mesh")
    postpass = row.get("live_thermal_state_hydraulic_postpass") or {}
    breakdown = row.get("hydraulic_dp_breakdown") or {}

    if full_converged and duty is not None:
        duty_constraint = "SATISFIED" if float(duty) >= float(target_duty_w) else "NOT_SATISFIED"
    else:
        duty_constraint = "NOT_FORMALLY_EVALUATED"

    tube_dp_constraint = postpass.get("tube_dp_constraint")
    shell_dp_constraint = postpass.get("shell_dp_constraint")
    if tube_dp_constraint is None and breakdown.get("TUBE_DP_MARGIN_PA") is not None:
        margin = Decimal(str(breakdown["TUBE_DP_MARGIN_PA"]))
        tube_dp_constraint = "SATISFIED" if margin >= 0 else "NOT_SATISFIED"
    if shell_dp_constraint is None and breakdown.get("SHELL_DP_MARGIN_PA") is not None:
        margin = Decimal(str(breakdown["SHELL_DP_MARGIN_PA"]))
        shell_dp_constraint = "SATISFIED" if margin >= 0 else "NOT_SATISFIED"

    tube_margin = row.get("TUBE_DP_MARGIN_PA") or breakdown.get("TUBE_DP_MARGIN_PA")
    shell_margin = row.get("SHELL_DP_MARGIN_PA") or breakdown.get("SHELL_DP_MARGIN_PA")

    return {
        "target_duty_w": str(target_duty_w),
        "duty_w_at_finest_mesh": duty,
        "duty_constraint": duty_constraint,
        "duty_constraint_basis": (
            "FULL_MESH_RATING" if full_converged else "NOT_FORMALLY_EVALUATED"
        ),
        "tube_dp_constraint": tube_dp_constraint,
        "shell_dp_constraint": shell_dp_constraint,
        "tube_dp_margin_pa": tube_margin,
        "shell_dp_margin_pa": shell_margin,
        "hydraulic_constraint_status": postpass.get("hydraulic_constraint_status"),
        "nominal_experimental_sizing_feasible": row.get("NOMINAL_EXPERIMENTAL_SIZING_FEASIBLE"),
    }


def _classify_candidate_feasibility(
    row: dict[str, Any],
    *,
    authorized_full_path: dict[str, Any] | None,
) -> dict[str, Any]:
    participation = row.get("rating_participation_status")
    if participation == "NOT_SELECTED_FOR_RATING":
        return {
            "feasibility_class": "NOT_RATED_THIS_RUN",
            "basis": "Not selected under solver_budget.max_candidates_to_rate; not eliminated.",
        }
    if participation != "FULLY_RATED" or row.get("FULL_RATING_CONVERGED") is not True:
        return {
            "feasibility_class": "PARTIAL_RATING_ONLY",
            "basis": "Only screening or partial mesh rating; constraints not formally closed.",
        }
    if row.get("NOMINAL_EXPERIMENTAL_SIZING_FEASIBLE"):
        thermal_class: CandidateFeasibilityClass = "THERMAL_AND_PARTIAL_HYDRAULIC_NOMINAL"
        basis = (
            "Full mesh thermal rating converged; live post-pass nominal hydraulic constraints "
            "satisfied for partial path model."
        )
    else:
        thermal_class = "PARTIAL_RATING_ONLY"
        basis = (
            "Full mesh rating completed but nominal experimental sizing comparison not feasible."
        )

    auth = authorized_full_path or {}
    demo_path = {
        "feasibility_class": "DEMONSTRATION_FULL_PATH_COMPARISON_ONLY",
        "basis": (
            "Authorized full-path hydraulic uses R26G demonstration EngineeringHydraulicPathInputV1; "
            "comparison valid only under those disclosed assumptions."
        ),
        "authorized_status": auth.get("status"),
    }
    return {
        "thermal_and_partial_hydraulic": {
            "feasibility_class": thermal_class,
            "basis": basis,
        },
        "demonstration_full_path": demo_path,
        "eligible_for_formal_constraint_ranking": thermal_class
        == "THERMAL_AND_PARTIAL_HYDRAULIC_NOMINAL",
    }


def estimate_preliminary_nozzle_diameters(
    case: EngineeringCase,
    *,
    velocity_rule: dict[str, Any] | None = None,
    provider: CoolPropProvider | None = None,
) -> dict[str, Any]:
    """Preliminary nozzle ID from mass flow, CoolProp density, and configurable velocity band."""
    rule = velocity_rule or NOZZLE_VELOCITY_DESIGN_RULE
    v_min = float(rule["velocity_m_s_min"])
    v_max = float(rule["velocity_m_s_max"])
    prov = provider or CoolPropProvider()
    sides: dict[str, Any] = {}
    for role, spec in (
        ("tube_side", tube_stream_spec(case)),
        ("shell_side", shell_stream_spec(case)),
    ):
        t_k = float(spec.inlet_temperature_k)
        p_pa = float(spec.inlet_pressure_pa)
        m_kg_s = float(spec.mass_flow_kg_s)
        state = prov.state_tp(FluidIdentifier("Water", "HEOS"), t_k, p_pa)
        rho = float(state.density_kg_m3)
        candidates: list[dict[str, Any]] = []
        for label, v in (
            ("min_velocity", v_min),
            ("max_velocity", v_max),
            ("mid_band", (v_min + v_max) / 2),
        ):
            area = m_kg_s / (rho * v)
            d_m = math.sqrt(4.0 * area / math.pi)
            candidates.append(
                {
                    "velocity_assumption_m_s": v,
                    "assumption_label": label,
                    "inside_diameter_m": d_m,
                    "actual_velocity_m_s": v,
                }
            )
        sides[role] = {
            "mass_flow_kg_s": m_kg_s,
            "inlet_density_kg_m3": rho,
            "density_source": "CoolProp HEOS at case inlet T,P",
            "diameter_candidates_m": candidates,
        }
    return {
        "schema_version": "hxforge.r27a-preliminary-nozzle-sizing.v1",
        "velocity_design_rule": rule,
        "local_loss_coefficients": {
            "status": "NOT_SUPPLIED_AS_REAL_DESIGN",
            "disclosure": (
                "No reliable K values asserted; tube local losses follow case engineering "
                "spec when present, otherwise report unmodeled segments separately."
            ),
        },
        "sides": sides,
    }


def _sizing_candidate_snapshot(
    *,
    case: EngineeringCase,
    row: dict[str, Any],
    authorized_full_path: dict[str, Any] | None,
) -> dict[str, Any]:
    geometry = _geometry_report_block(row=row, case=case)
    task171_area = row.get("task171_total_outside_area_m2")
    proxy_area = geometry.get("nominal_tube_outer_area_proxy_m2")
    area_for_u = float(task171_area) if task171_area is not None else None
    area_for_u_label = "task171_rated_outside_area_m2"
    if area_for_u is None and proxy_area is not None:
        area_for_u = float(proxy_area)
        area_for_u_label = "nominal_tube_outer_area_proxy_m2_NOT_TASK171"

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
    u_equiv = None
    if row.get("FULL_RATING_CONVERGED") is True and duty is not None:
        u_equiv = _counterflow_equivalent_u_w_m2_k(
            duty_w=float(duty),
            area_m2=area_for_u,
            lmtd_k=lmtd,
        )
    breakdown = row.get("hydraulic_dp_breakdown")
    return {
        "candidate_id": row["candidate_id"],
        "candidate_hash": row.get("candidate_hash"),
        "rating_participation_status": row.get("rating_participation_status"),
        "geometry": geometry,
        "thermal_rating": {
            "duty_w": duty,
            "tube_outlet_temperature_k": tube_out,
            "shell_outlet_temperature_k": shell_out,
            "full_rating_converged": row.get("FULL_RATING_CONVERGED"),
            "counterflow_lmtd_k": lmtd,
            "counterflow_equivalent_u_w_m2_k": u_equiv,
            "counterflow_equivalent_u_definition": (
                "Q/(A·LMTD_counterflow) from finest-mesh duty and rated outlet temperatures; "
                "counterflow equivalent screening metric only — not formal TEMA overall U."
            ),
            "counterflow_equivalent_u_area_source": area_for_u_label,
        },
        "hydraulic_performance": {
            "live_tube_dp_pa": row.get("LIVE_TUBE_DP_PA"),
            "live_shell_dp_pa": row.get("LIVE_SHELL_DP_PA"),
            "tube_dp_margin_pa": row.get("TUBE_DP_MARGIN_PA"),
            "shell_dp_margin_pa": row.get("SHELL_DP_MARGIN_PA"),
            "hydraulic_dp_breakdown": breakdown,
            "authorized_full_path_hydraulic": authorized_full_path,
            "authorized_path_input_basis": (
                "R26G_DEMONSTRATION_ENGINEERING_HYDRAULIC_PATH_INPUT_V1"
                if authorized_full_path
                else None
            ),
        },
        "constraints": _constraint_summary(row, target_duty_w=Decimal(str(case.target_duty_w))),
        "feasibility_classification": _classify_candidate_feasibility(
            row, authorized_full_path=authorized_full_path
        ),
        "elimination_or_incomplete_reason": row.get("elimination_reason"),
        "is_candidate_b_baseline_geometry": row.get("is_candidate_b_baseline_geometry"),
    }


def _recommendation_block(
    multi: dict[str, Any],
    sizing_rows: list[dict[str, Any]],
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
    formal_rank_ids = [
        row["candidate_id"]
        for row in sizing_rows
        if row.get("feasibility_classification", {}).get("eligible_for_formal_constraint_ranking")
    ]
    demo_rank_ids = [
        row["candidate_id"]
        for row in sizing_rows
        if (
            (row.get("hydraulic_performance") or {}).get("authorized_full_path_hydraulic") or {}
        ).get("status")
        == "COMPUTED"
    ]
    return {
        "recommended_candidate_id": best_in_run,
        "recommendation_scope": "BEST_NOMINAL_FEASIBLE_FULLY_RATED_IN_THIS_RUN",
        "formal_constraint_ranking_candidate_ids": formal_rank_ids,
        "demonstration_full_path_comparison_candidate_ids": demo_rank_ids,
        "demonstration_ranking_disclosure": (
            "Demonstration full-path IDs use R26G demo path inputs and must not be merged "
            "into formal constraint ranking."
        ),
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
    nominal_feasible = multi.get("NOMINAL_FEASIBLE_COUNT", 0) or 0

    return {
        "schema_version": _SCHEMA,
        "TASK_ID": _TASK_ID,
        "generated_at_utc": datetime.now(tz=UTC).isoformat(),
        "SIZING_TARGET_AUTHORITY": _SIZING_AUTHORITY,
        "PRODUCTION_DESIGN_APPROVED": False,
        "ENGINEERING_SIZING_ELIGIBILITY": "DEMONSTRATION_ONLY_NOT_ENGINEERING_SIZING_ELIGIBLE",
        "user_design_input": design_conditions_for_report(case),
        "preliminary_nozzle_sizing": estimate_preliminary_nozzle_diameters(case),
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
            "NOMINAL_FEASIBLE_COUNT": nominal_feasible,
        },
        "recommendation": _recommendation_block(multi, sizing_rows, selection=selection),
        "sizing_candidates": sizing_rows,
        "experimental_tradeoff_comparison": multi.get("experimental_tradeoff_comparison"),
        "engineering_comparison_report": multi.get("engineering_comparison_report"),
        "sizing_calculation_status": "SIZING_CALCULATION_COMPLETE",
        "found_feasible_design": (
            "FOUND_FEASIBLE_DESIGN" if nominal_feasible >= 1 else "NO_NOMINAL_FEASIBLE_DESIGN"
        ),
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
            "Counterflow equivalent U is not a formal overall heat-transfer coefficient.",
        ],
    }


def render_calculation_first_sizing_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# Calculation-first automatic sizing — {report['TASK_ID']}",
        "",
        f"Generated (UTC): {report['generated_at_utc']}",
        "",
        f"- Sizing calculation: **{report.get('sizing_calculation_status')}**",
        f"- Feasible design: **{report.get('found_feasible_design')}**",
        "",
        "## Design input",
        "",
    ]
    dc = report["user_design_input"]
    lines.append(f"- Target duty: **{dc['target_duty_w']} W**")
    lines.append(f"- Max tube Δp: **{dc['max_tube_dp_pa']} Pa**")
    lines.append(f"- Max shell Δp: **{dc['max_shell_dp_pa']} Pa**")
    lines.append("")
    nozzle = report.get("preliminary_nozzle_sizing") or {}
    rule = nozzle.get("velocity_design_rule") or {}
    lines.extend(
        [
            "## Preliminary nozzle sizing (assumption-based)",
            "",
            f"- Velocity rule: {rule.get('rule_id')} ({rule.get('velocity_m_s_min')}–"
            f"{rule.get('velocity_m_s_max')} m/s)",
            f"- {rule.get('disclosure', '')}",
            "",
        ]
    )
    for side_key, side in (nozzle.get("sides") or {}).items():
        mid = next(
            (
                c
                for c in side.get("diameter_candidates_m") or []
                if c.get("assumption_label") == "mid_band"
            ),
            None,
        )
        if mid:
            lines.append(
                f"- {side_key}: ρ={side.get('inlet_density_kg_m3'):.1f} kg/m³, "
                f"mid-band ID ≈ {mid['inside_diameter_m']:.4f} m @ {mid['velocity_assumption_m_s']} m/s"
            )
    lines.append("")
    rec = report["recommendation"]
    lines.extend(
        [
            "## Recommendation (scoped to this run)",
            "",
            f"- Recommended candidate: `{rec.get('recommended_candidate_id')}`",
            f"- Formal constraint ranking IDs: {rec.get('formal_constraint_ranking_candidate_ids')}",
            f"- Demo full-path comparison IDs: {rec.get('demonstration_full_path_comparison_candidate_ids')}",
            f"- {rec.get('demonstration_ranking_disclosure')}",
            "",
            "## Candidates",
            "",
            "| ID (short) | Status | Duty W | T_out tube/shell K | Area proxy / Task171 m² | Δp tube/shell Pa | Margins Pa | Duty constr |",
            "|---|---|---:|---|---|---:|---|---|---|",
        ]
    )
    for row in report["sizing_candidates"]:
        geom = row["geometry"]
        therm = row["thermal_rating"]
        hyd = row["hydraulic_performance"]
        constr = row["constraints"]
        cid = row["candidate_id"][:8]
        proxy = geom.get("nominal_tube_outer_area_proxy_m2")
        t171 = geom.get("task171_rated_outside_area_m2")
        u_note = therm.get("counterflow_equivalent_u_w_m2_k")
        lines.append(
            f"| `{cid}` | {row['rating_participation_status']} | {therm.get('duty_w')} | "
            f"{therm.get('tube_outlet_temperature_k')}/{therm.get('shell_outlet_temperature_k')} | "
            f"{proxy}/{t171} | {hyd.get('live_tube_dp_pa')}/{hyd.get('live_shell_dp_pa')} | "
            f"{constr.get('tube_dp_margin_pa')}/{constr.get('shell_dp_margin_pa')} | "
            f"{constr.get('duty_constraint')} |"
        )
        lines.append(
            f"  - Geometry: shell ID {geom.get('shell_inside_diameter_m')} m, "
            f"L {geom.get('tube_length_m')} m, tubes {geom.get('physical_tube_count')}, "
            f"baffles {geom.get('baffle_count', {}).get('value')} @ spacing "
            f"{geom.get('baffle_spacing_m')} m, passes {geom.get('tube_pass_count', {}).get('value')}"
        )
        lines.append(
            f"  - U_cf_equiv: {u_note} W/m²K ({therm.get('counterflow_equivalent_u_area_source')}) — "
            f"{therm.get('counterflow_equivalent_u_definition')}"
        )
        fc = row.get("feasibility_classification") or {}
        lines.append(
            f"  - Feasibility: {fc.get('thermal_and_partial_hydraulic', {}).get('feasibility_class')} / "
            f"demo path {fc.get('demonstration_full_path', {}).get('authorized_status')}"
        )
    lines.append("")
    for warn in report.get("engineering_warnings") or []:
        lines.append(f"- Warning: {warn}")
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
