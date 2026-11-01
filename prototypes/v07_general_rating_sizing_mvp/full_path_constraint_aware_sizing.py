"""R27B: full-path constraint-aware calculation-first automatic sizing."""

# ruff: noqa: E501

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from prototypes.v07_general_rating_sizing_mvp.authorized_full_path_hydraulic_calculation import (
    run_authorized_full_path_hydraulic_calculation,
)
from prototypes.v07_general_rating_sizing_mvp.calculation_first_automatic_sizing import (
    _constraint_summary,
    _counterflow_equivalent_u_w_m2_k,
    _counterflow_lmtd_k,
    _geometry_report_block,
    _record_map,
    estimate_preliminary_nozzle_diameters,
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
    R27B_ASSUMPTION_LOSS_COEFFICIENT_SCENARIOS,
    build_r27b_assumption_based_hydraulic_path_input_v1,
    nozzle_flow_area_m2,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_multi_candidate_engineering_sizing import (
    run_experimental_multi_candidate_engineering_sizing,
)

_TASK_ID = "V07_R27B_FULL_PATH_CONSTRAINT_AWARE_SIZING"
_SCHEMA = "hxforge.full-path-constraint-aware-sizing.v27b"
_SIZING_AUTHORITY = "EXPERIMENTAL_CALCULATION_FIRST_NOT_PRODUCTION_APPROVED"

REFERENCE_GEOMETRY_FINGERPRINTS: tuple[dict[str, str], ...] = (
    {"label": "Candidate B", "shell_inside_diameter_m": "0.56", "tube_length_m": "3.0"},
    {"label": "0.54m short tube", "shell_inside_diameter_m": "0.54", "tube_length_m": "3.0"},
    {"label": "0.54m intermediate 3.5m", "shell_inside_diameter_m": "0.54", "tube_length_m": "3.5"},
)


def find_short_reference_record(
    selection: CandidateSelectionOutcome,
) -> CandidateSelectionRecord | None:
    return next(
        (
            r
            for r in selection.records
            if r.rating_request_ready
            and r.tube_length_m == "3.0"
            and r.shell_inside_diameter_m == "0.54"
            and r.physical_tube_count == 313
        ),
        None,
    )


def _nozzle_used_for_path(
    preliminary: dict[str, Any],
) -> dict[str, Any]:
    sides_out: dict[str, Any] = {}
    for side_key in ("tube_side", "shell_side"):
        side = preliminary["sides"][side_key]
        mid = next(
            c for c in side["diameter_candidates_m"] if c.get("assumption_label") == "mid_band"
        )
        d_m = float(mid["inside_diameter_m"])
        rho = float(side["inlet_density_kg_m3"])
        m = float(side["mass_flow_kg_s"])
        area = float(nozzle_flow_area_m2(Decimal(str(d_m))))
        velocity = m / (rho * area)
        sides_out[side_key] = {
            "assumption_label": "mid_band",
            "inside_diameter_m": d_m,
            "reference_flow_area_m2": area,
            "actual_velocity_m_s": velocity,
            "inlet_density_kg_m3": rho,
            "mass_flow_kg_s": m,
        }
    return {
        "velocity_design_rule": preliminary.get("velocity_design_rule"),
        "loss_coefficient_scenarios": {
            key: {
                "scenario_id": val["scenario_id"],
                "source_nature": val["source_nature"],
                "disclosure": val["disclosure"],
            }
            for key, val in R27B_ASSUMPTION_LOSS_COEFFICIENT_SCENARIOS.items()
        },
        "active_loss_scenario_key": "mid_band",
        "sides": sides_out,
        "input_authority": "ASSUMPTION_BASED",
    }


def _hydraulic_pressure_budget(
    *,
    partial_breakdown: dict[str, Any] | None,
    full_path: dict[str, Any] | None,
    case: EngineeringCase,
) -> dict[str, Any]:
    partial = partial_breakdown or {}
    auth = full_path or {}
    max_tube = float(case.max_tube_side_pressure_drop_pa)
    max_shell = float(case.max_shell_side_pressure_drop_pa)

    def _f(key: str) -> float | None:
        raw = auth.get(key) or partial.get(key)
        if raw is None:
            return None
        return float(raw)

    tube_friction = _f("TUBE_INTERNAL_FRICTION_DP_PA")
    tube_local = _f("TUBE_LOCAL_DP_PA")
    tube_partial = _f("TUBE_MODELED_PARTIAL_DP_PA")
    tube_full = _f("TUBE_FULL_PATH_TOTAL_DP_PA")
    shell_bd = _f("SHELL_BELL_DELAWARE_INTERNAL_DP_PA") or _f("SHELL_INTERNAL_DP_PA")
    shell_external = _f("SHELL_EXTERNAL_LOCAL_DP_PA")
    shell_partial = _f("SHELL_MODELED_PARTIAL_DP_PA")
    shell_full = _f("SHELL_FULL_PATH_TOTAL_DP_PA")

    uncovered: list[str] = []
    if partial.get("SHELL_FULL_PATH_STATUS") == "ENGINEERING_GEOMETRY_INPUT_REQUIRED":
        uncovered.append("Partial breakdown shell nozzle path not modeled separately.")
    if auth.get("path_completeness", {}).get("FULL_PATH_VERIFICATION_STATUS") == "NOT_VERIFIED":
        uncovered.append(
            "Full-path completeness is assumption-based; mechanical/vibration/code not verified."
        )

    return {
        "tube_side": {
            "internal_friction_dp_pa": tube_friction,
            "local_loss_dp_pa": tube_local,
            "modeled_partial_total_dp_pa": tube_partial,
            "full_path_total_dp_pa": tube_full,
            "remaining_margin_partial_pa": (
                max_tube - tube_partial if tube_partial is not None else None
            ),
            "remaining_margin_full_path_pa": (
                float(auth["TUBE_FULL_PATH_DP_MARGIN_PA"])
                if auth.get("TUBE_FULL_PATH_DP_MARGIN_PA") is not None
                else (max_tube - tube_full if tube_full is not None else None)
            ),
        },
        "shell_side": {
            "bell_delaware_internal_dp_pa": shell_bd,
            "external_local_and_nozzle_dp_pa": shell_external,
            "modeled_partial_total_dp_pa": shell_partial,
            "full_path_total_dp_pa": shell_full,
            "remaining_margin_partial_pa": (
                max_shell - shell_partial if shell_partial is not None else None
            ),
            "remaining_margin_full_path_pa": (
                float(auth["SHELL_FULL_PATH_DP_MARGIN_PA"])
                if auth.get("SHELL_FULL_PATH_DP_MARGIN_PA") is not None
                else (max_shell - shell_full if shell_full is not None else None)
            ),
        },
        "uncovered_or_not_modeled_losses": uncovered,
        "PRODUCTION_DESIGN_APPROVED": False,
    }


def _full_path_feasible(
    *,
    constraints: dict[str, Any],
    full_path: dict[str, Any] | None,
) -> tuple[bool, list[str]]:
    violations: list[str] = []
    if constraints.get("duty_constraint") != "SATISFIED":
        violations.append(f"DUTY_{constraints.get('duty_constraint', 'NOT_EVALUATED')}")
    auth = full_path or {}
    if auth.get("status") != "COMPUTED":
        violations.append(f"FULL_PATH_STATUS_{auth.get('status', 'MISSING')}")
    tube_c = auth.get("FULL_PATH_TUBE_CONSTRAINT_STATUS")
    shell_c = auth.get("FULL_PATH_SHELL_CONSTRAINT_STATUS")
    combined = auth.get("FULL_PATH_HYDRAULIC_STATUS")
    if tube_c != "SATISFIED":
        violations.append(f"FULL_PATH_TUBE_{tube_c or 'NOT_EVALUATED'}")
    if shell_c != "SATISFIED":
        violations.append(f"FULL_PATH_SHELL_{shell_c or 'NOT_EVALUATED'}")
    if combined != "SATISFIED":
        violations.append(f"FULL_PATH_HYDRAULIC_{combined or 'NOT_EVALUATED'}")
    return not violations, violations


def _rank_full_path_feasible(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    feasible = [r for r in rows if r.get("full_path_constraint_ranking", {}).get("feasible")]
    if not feasible:
        return []

    def sort_key(row: dict[str, Any]) -> tuple[float, float, float, float]:
        budget = row.get("hydraulic_pressure_budget") or {}
        tube_m = budget.get("tube_side", {}).get("remaining_margin_full_path_pa")
        shell_m = budget.get("shell_side", {}).get("remaining_margin_full_path_pa")
        area = row.get("geometry", {}).get("task171_rated_outside_area_m2")
        tube_m_f = float(tube_m) if tube_m is not None else -1e9
        shell_m_f = float(shell_m) if shell_m is not None else -1e9
        area_f = float(area) if area is not None else 1e9
        min_margin = min(tube_m_f, shell_m_f)
        return (-min_margin, area_f, -tube_m_f, -shell_m_f)

    return sorted(feasible, key=sort_key)


def _sizing_candidate_snapshot_r27b(
    *,
    case: EngineeringCase,
    row: dict[str, Any],
    full_path: dict[str, Any] | None,
    path_input_summary: dict[str, Any] | None,
    preliminary_nozzle: dict[str, Any],
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
    constraints = _constraint_summary(row, target_duty_w=Decimal(str(case.target_duty_w)))
    feasible, violations = _full_path_feasible(constraints=constraints, full_path=full_path)
    budget = _hydraulic_pressure_budget(
        partial_breakdown=breakdown,
        full_path=full_path,
        case=case,
    )

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
            "full_path_hydraulic": full_path,
            "hydraulic_pressure_budget": budget,
            "path_input_basis": "R27B_ASSUMPTION_BASED_ENGINEERING_HYDRAULIC_PATH_INPUT_V1",
            "path_input_summary": path_input_summary,
            "nozzle_geometry_used_in_full_path": _nozzle_used_for_path(preliminary_nozzle),
        },
        "constraints": constraints,
        "full_path_constraint_ranking": {
            "feasible": feasible,
            "constraint_violations": violations,
            "ranking_basis": (
                "Thermal duty at finest mesh and R27B assumption-based full-path Δp vs case limits."
            ),
        },
        "elimination_or_incomplete_reason": row.get("elimination_reason"),
        "is_candidate_b_baseline_geometry": row.get("is_candidate_b_baseline_geometry"),
    }


def run_full_path_constraint_aware_sizing(
    case: EngineeringCase,
    *,
    max_candidates: int | None = None,
    loss_scenario_key: str = "mid_band",
    precomputed_selection: CandidateSelectionOutcome | None = None,
) -> dict[str, Any]:
    """Design → candidates → rating → R27B full-path hydraulics → constraint-aware recommendation."""
    selection = precomputed_selection or enumerate_experimental_rating_candidates(case)
    preliminary_nozzle = estimate_preliminary_nozzle_diameters(case)
    multi = run_experimental_multi_candidate_engineering_sizing(
        case,
        max_candidates=max_candidates,
        run_full_mesh_hydraulic=True,
        precomputed_selection=selection,
    )
    records = _record_map(selection)
    rate_ids = list(selection.selected_candidate_ids)
    if max_candidates is not None:
        rate_ids = rate_ids[:max_candidates]
    rate_id_set = set(rate_ids)

    full_path_by_id: dict[str, dict[str, Any]] = {}
    path_summary_by_id: dict[str, dict[str, Any]] = {}
    for candidate_id in rate_id_set:
        row = next((r for r in multi["candidates"] if r["candidate_id"] == candidate_id), None)
        if row is None or row.get("FULL_RATING_CONVERGED") is not True:
            continue
        record = records.get(candidate_id)
        if record is None or not record.rating_request_ready:
            continue
        path_input = build_r27b_assumption_based_hydraulic_path_input_v1(
            case=case,
            record=record,
            preliminary_nozzle_sizing=preliminary_nozzle,
            loss_scenario_key=loss_scenario_key,
        )
        path_summary_by_id[candidate_id] = {
            "loss_scenario_key": loss_scenario_key,
            "scenario_id": R27B_ASSUMPTION_LOSS_COEFFICIENT_SCENARIOS[loss_scenario_key][
                "scenario_id"
            ],
            "tube_component_count": len(path_input.tube_side_components),
            "shell_external_component_count": len(path_input.shell_external_components),
            "engineering_input_status": "ASSUMPTION_BASED",
        }
        full_path_by_id[candidate_id] = run_authorized_full_path_hydraulic_calculation(
            case=case,
            path_input=path_input,
            record=record,
            postpass=row.get("live_thermal_state_hydraulic_postpass"),
        )

    sizing_rows = [
        _sizing_candidate_snapshot_r27b(
            case=case,
            row=row,
            full_path=full_path_by_id.get(row["candidate_id"]),
            path_input_summary=path_summary_by_id.get(row["candidate_id"]),
            preliminary_nozzle=preliminary_nozzle,
        )
        for row in multi["candidates"]
    ]

    ranked = _rank_full_path_feasible(
        [r for r in sizing_rows if r["rating_participation_status"] == "FULLY_RATED"]
    )
    if ranked:
        recommended_id = ranked[0]["candidate_id"]
        found_status = "FOUND_FULL_PATH_FEASIBLE_DESIGN"
        recommendation_scope = "BEST_FULL_PATH_FEASIBLE_THEN_HYDRAULIC_MARGIN_AND_AREA"
    else:
        recommended_id = None
        found_status = "NO_FULL_PATH_FEASIBLE_CANDIDATE"
        recommendation_scope = "NO_FULL_PATH_FEASIBLE_IN_SEARCHED_SPACE"

    infeasible_details = [
        {
            "candidate_id": row["candidate_id"],
            "violations": row["full_path_constraint_ranking"]["constraint_violations"],
        }
        for row in sizing_rows
        if row.get("rating_participation_status") == "FULLY_RATED"
        and not row["full_path_constraint_ranking"]["feasible"]
    ]

    return {
        "schema_version": _SCHEMA,
        "TASK_ID": _TASK_ID,
        "generated_at_utc": datetime.now(tz=UTC).isoformat(),
        "SIZING_TARGET_AUTHORITY": _SIZING_AUTHORITY,
        "PRODUCTION_DESIGN_APPROVED": False,
        "ENGINEERING_SIZING_ELIGIBILITY": "ASSUMPTION_BASED_NOT_ENGINEERING_SIZING_ELIGIBLE",
        "user_design_input": design_conditions_for_report(case),
        "preliminary_nozzle_sizing": preliminary_nozzle,
        "assumption_loss_coefficient_policy": {
            "active_scenario_key": loss_scenario_key,
            "available_scenarios": list(R27B_ASSUMPTION_LOSS_COEFFICIENT_SCENARIOS.keys()),
            "input_authority": "ASSUMPTION_BASED",
            "disclosure": (
                "Loss coefficients and non-nozzle reference areas are configurable assumptions; "
                "results must not be treated as verified engineering design."
            ),
        },
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
        "recommendation": {
            "recommended_candidate_id": recommended_id,
            "recommendation_scope": recommendation_scope,
            "full_path_feasible_candidate_ids": [r["candidate_id"] for r in ranked],
            "ranked_full_path_feasible_candidate_ids": [r["candidate_id"] for r in ranked],
            "partial_nominal_feasible_candidate_ids": [
                row["candidate_id"]
                for row in sizing_rows
                if row.get("constraints", {}).get("nominal_experimental_sizing_feasible")
            ],
            "infeasible_full_path_details": infeasible_details,
            "ranking_disclosure": (
                "Primary filter: full mesh duty and assumption-based full-path Δp within case limits "
                "with CoolProp outlet domain satisfied. Tie-break: minimum hydraulic margin then area."
            ),
            "reference_geometry_fingerprints": list(REFERENCE_GEOMETRY_FINGERPRINTS),
        },
        "sizing_candidates": sizing_rows,
        "sizing_calculation_status": "SIZING_CALCULATION_COMPLETE",
        "found_feasible_design": found_status,
        "workflow_status": "SIZING_CALCULATION_COMPLETE",
        "model_applicability": {
            "fluid": "PURE_ORDINARY_WATER_SINGLE_PHASE",
            "construction": case.exchanger_type,
            "service_envelope": "Experimental MVP; assumption-based full-path sizing only.",
        },
        "engineering_warnings": [
            "R27B uses assumption-based hydraulic path inputs tied to R27A preliminary nozzle sizing.",
            "Partial-model hydraulic feasibility does not imply full-path feasibility.",
            "Demonstration R26G fixed-nozzle paths are not used for R27B formal ranking.",
            "Counterflow equivalent U is not a formal overall heat-transfer coefficient.",
        ],
    }


def render_full_path_constraint_aware_sizing_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# Full-path constraint-aware sizing — {report['TASK_ID']}",
        "",
        f"Generated (UTC): {report['generated_at_utc']}",
        "",
        f"- Status: **{report.get('sizing_calculation_status')}**",
        f"- Outcome: **{report.get('found_feasible_design')}**",
        "",
        "## Design input",
        "",
    ]
    dc = report["user_design_input"]
    lines.append(
        f"- Target duty: **{dc['target_duty_w']} W** ({float(dc['target_duty_w']) / 1000:.1f} kW)"
    )
    lines.append(f"- Max tube Δp: **{dc['max_tube_dp_pa']} Pa**")
    lines.append(f"- Max shell Δp: **{dc['max_shell_dp_pa']} Pa**")
    lines.append("")

    rec = report["recommendation"]
    lines.extend(
        [
            "## Recommendation (full-path constraint aware)",
            "",
            f"- Recommended: `{rec.get('recommended_candidate_id')}`",
            f"- Scope: {rec.get('recommendation_scope')}",
            f"- Full-path feasible IDs: {rec.get('full_path_feasible_candidate_ids')}",
            "",
            "## Rated candidates",
            "",
            "| ID | Duty kW | Partial tube/shell Pa | Full tube/shell Pa | Full-path status | Feasible |",
            "|---|---:|---:|---:|---|---|",
        ]
    )
    for row in report["sizing_candidates"]:
        if row["rating_participation_status"] != "FULLY_RATED":
            continue
        therm = row["thermal_rating"]
        hyd = row["hydraulic_performance"]
        fp = hyd.get("full_path_hydraulic") or {}
        duty_kw = float(therm["duty_w"]) / 1000 if therm.get("duty_w") else None
        lines.append(
            f"| `{row['candidate_id'][:8]}` | {duty_kw:.2f} | "
            f"{hyd.get('live_tube_dp_pa')}/{hyd.get('live_shell_dp_pa')} | "
            f"{fp.get('TUBE_FULL_PATH_TOTAL_DP_PA')}/{fp.get('SHELL_FULL_PATH_TOTAL_DP_PA')} | "
            f"{fp.get('FULL_PATH_HYDRAULIC_STATUS')} | "
            f"{row['full_path_constraint_ranking']['feasible']} |"
        )
        geom = row["geometry"]
        nozzle = hyd.get("nozzle_geometry_used_in_full_path", {}).get("sides", {})
        lines.append(
            f"  - Geometry: shell {geom.get('shell_inside_diameter_m')} m, "
            f"L {geom.get('tube_length_m')} m, tubes {geom.get('physical_tube_count')}, "
            f"Task171 area {geom.get('task171_rated_outside_area_m2')} m²"
        )
        for side in ("tube_side", "shell_side"):
            ns = nozzle.get(side) or {}
            if ns:
                lines.append(
                    f"  - Nozzle {side}: ID {ns.get('inside_diameter_m'):.4f} m, "
                    f"v≈{ns.get('actual_velocity_m_s'):.2f} m/s"
                )
        budget = hyd.get("hydraulic_pressure_budget") or {}
        ts = budget.get("tube_side") or {}
        ss = budget.get("shell_side") or {}
        lines.append(
            f"  - Budget margins (full path): tube {ts.get('remaining_margin_full_path_pa')} Pa, "
            f"shell {ss.get('remaining_margin_full_path_pa')} Pa"
        )
        if not row["full_path_constraint_ranking"]["feasible"]:
            lines.append(
                f"  - Violations: {row['full_path_constraint_ranking']['constraint_violations']}"
            )

    if (
        rec.get("found_feasible_design") == "NO_FULL_PATH_FEASIBLE_CANDIDATE"
        or report.get("found_feasible_design") == "NO_FULL_PATH_FEASIBLE_CANDIDATE"
    ):
        lines.extend(["", "## Infeasible full-path details", ""])
        for item in rec.get("infeasible_full_path_details") or []:
            lines.append(f"- `{item['candidate_id']}`: {item['violations']}")

    lines.append("")
    for warn in report.get("engineering_warnings") or []:
        lines.append(f"- Warning: {warn}")
    return "\n".join(lines) + "\n"


def write_full_path_constraint_aware_sizing_reports(
    report: dict[str, Any],
    output_dir: Path,
    *,
    basename: str = "R27B_FULL_PATH_CONSTRAINT_AWARE_SIZING",
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{basename}.json"
    md_path = output_dir / f"{basename}.md"
    json_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    md_path.write_text(render_full_path_constraint_aware_sizing_markdown(report), encoding="utf-8")
    return json_path, md_path
