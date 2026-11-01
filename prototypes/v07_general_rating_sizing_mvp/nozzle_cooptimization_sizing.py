"""R27C: joint bundle + nozzle pressure-budget co-optimization sizing report."""

# ruff: noqa: E501

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

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
)
from prototypes.v07_general_rating_sizing_mvp.experimental_multi_candidate_engineering_sizing import (
    run_experimental_multi_candidate_engineering_sizing,
)
from prototypes.v07_general_rating_sizing_mvp.full_path_constraint_aware_sizing import (
    REFERENCE_GEOMETRY_FINGERPRINTS,
)
from prototypes.v07_general_rating_sizing_mvp.nozzle_pressure_budget_solver import (
    LossScenarioKey,
    cooptimize_nozzles_for_candidate_scenario,
)

_TASK_ID = "V07_R27C_NOZZLE_PRESSURE_BUDGET_CO_OPTIMIZATION"
_SCHEMA = "hxforge.nozzle-pressure-budget-cooptimization.v27c"
_SIZING_AUTHORITY = "EXPERIMENTAL_CALCULATION_FIRST_NOT_PRODUCTION_APPROVED"

LOSS_SCENARIO_KEYS: tuple[LossScenarioKey, ...] = (
    "mid_band",
    "low_loss_sensitivity",
    "high_loss_sensitivity",
)


def _thermal_block_from_row(row: dict[str, Any], *, case: EngineeringCase) -> dict[str, Any]:
    geometry = _geometry_report_block(row=row, case=case)
    task171_area = row.get("task171_total_outside_area_m2")
    proxy_area = geometry.get("nominal_tube_outer_area_proxy_m2")
    area_for_u = float(task171_area) if task171_area is not None else None
    if area_for_u is None and proxy_area is not None:
        area_for_u = float(proxy_area)

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
    return {
        "duty_w": duty,
        "tube_outlet_temperature_k": tube_out,
        "shell_outlet_temperature_k": shell_out,
        "full_rating_converged": row.get("FULL_RATING_CONVERGED"),
        "counterflow_lmtd_k": lmtd,
        "counterflow_equivalent_u_w_m2_k": u_equiv,
    }


def _rank_candidates(
    sizing_rows: list[dict[str, Any]],
    *,
    scenario_key: LossScenarioKey = "mid_band",
) -> list[dict[str, Any]]:
    feasible = [
        row
        for row in sizing_rows
        if row.get("rating_participation_status") == "FULLY_RATED"
        and (row.get("loss_scenario_results") or {}).get(scenario_key, {}).get("full_path_feasible")
    ]

    def key(row: dict[str, Any]) -> tuple[float, float]:
        sc = row["loss_scenario_results"][scenario_key]
        fp = sc.get("full_path_hydraulic_verification") or {}
        tube_m = fp.get("TUBE_FULL_PATH_DP_MARGIN_PA")
        shell_m = fp.get("SHELL_FULL_PATH_DP_MARGIN_PA")
        area = row.get("geometry", {}).get("task171_rated_outside_area_m2")
        t_m = float(tube_m) if tube_m is not None else -1e9
        s_m = float(shell_m) if shell_m is not None else -1e9
        return (-min(t_m, s_m), float(area) if area is not None else 1e9)

    return sorted(feasible, key=key)


def run_nozzle_pressure_budget_cooptimization(
    case: EngineeringCase,
    *,
    max_candidates: int | None = None,
    precomputed_selection: CandidateSelectionOutcome | None = None,
) -> dict[str, Any]:
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

    sizing_rows: list[dict[str, Any]] = []
    for row in multi["candidates"]:
        geometry = _geometry_report_block(row=row, case=case)
        thermal = _thermal_block_from_row(row, case=case)
        constraints = _constraint_summary(row, target_duty_w=Decimal(str(case.target_duty_w)))
        scenario_results: dict[str, Any] = {}
        if (
            row["candidate_id"] in rate_id_set
            and row.get("FULL_RATING_CONVERGED") is True
            and row.get("rating_participation_status") == "FULLY_RATED"
        ):
            record = records[row["candidate_id"]]
            postpass = row.get("live_thermal_state_hydraulic_postpass") or {}
            for scenario_key in LOSS_SCENARIO_KEYS:
                scenario_results[scenario_key] = cooptimize_nozzles_for_candidate_scenario(
                    case=case,
                    record=record,
                    postpass=postpass,
                    loss_scenario_key=scenario_key,
                )

        sizing_rows.append(
            {
                "candidate_id": row["candidate_id"],
                "candidate_hash": row.get("candidate_hash"),
                "rating_participation_status": row.get("rating_participation_status"),
                "geometry": geometry,
                "thermal_rating": thermal,
                "hydraulic_performance": {
                    "live_tube_dp_pa": row.get("LIVE_TUBE_DP_PA"),
                    "live_shell_dp_pa": row.get("LIVE_SHELL_DP_PA"),
                    "tube_dp_margin_pa": row.get("TUBE_DP_MARGIN_PA"),
                    "shell_dp_margin_pa": row.get("SHELL_DP_MARGIN_PA"),
                    "hydraulic_dp_breakdown": row.get("hydraulic_dp_breakdown"),
                    "partial_model_internal_disclosure": (
                        "Live tube/shell dp are bundle partial-model values from rating post-pass; "
                        "unchanged by R27C nozzle co-optimization."
                    ),
                },
                "constraints": constraints,
                "loss_scenario_results": scenario_results,
                "failure_attribution_hints": _failure_hints(scenario_results, constraints),
            }
        )

    ranked_mid = _rank_candidates(sizing_rows, scenario_key="mid_band")
    if ranked_mid:
        recommended_id = ranked_mid[0]["candidate_id"]
        found = "FOUND_FULL_PATH_FEASIBLE_DESIGN"
        scope = "BEST_FULL_PATH_FEASIBLE_MID_BAND_SCENARIO"
    else:
        recommended_id = None
        found = "NO_FULL_PATH_FEASIBLE_CANDIDATE"
        scope = "NO_FEASIBLE_NOZZLE_AND_BUNDLE_COMBINATION_IN_SEARCHED_SPACE"

    return {
        "schema_version": _SCHEMA,
        "TASK_ID": _TASK_ID,
        "generated_at_utc": datetime.now(tz=UTC).isoformat(),
        "PRODUCTION_DESIGN_APPROVED": False,
        "ENGINEERING_SIZING_ELIGIBILITY": "ASSUMPTION_BASED_NOT_ENGINEERING_SIZING_ELIGIBLE",
        "user_design_input": design_conditions_for_report(case),
        "preliminary_nozzle_sizing_reference": preliminary_nozzle,
        "loss_coefficient_scenarios": {
            key: {
                "scenario_id": val["scenario_id"],
                "disclosure": val["disclosure"],
                "ASSUMPTION_BASED": True,
            }
            for key, val in R27B_ASSUMPTION_LOSS_COEFFICIENT_SCENARIOS.items()
        },
        "recommendation": {
            "recommended_candidate_id": recommended_id,
            "recommendation_scope": scope,
            "primary_ranking_scenario_key": "mid_band",
            "ranked_full_path_feasible_mid_band_ids": [r["candidate_id"] for r in ranked_mid],
            "per_scenario_feasible_candidate_ids": {
                key: [
                    row["candidate_id"]
                    for row in sizing_rows
                    if (row.get("loss_scenario_results") or {})
                    .get(key, {})
                    .get("full_path_feasible")
                ]
                for key in LOSS_SCENARIO_KEYS
            },
            "reference_geometry_fingerprints": list(REFERENCE_GEOMETRY_FINGERPRINTS),
            "disclosure": (
                "Each K scenario is evaluated independently; mid_band alone drives primary ranking."
            ),
        },
        "sizing_candidates": sizing_rows,
        "found_feasible_design": found,
        "sizing_calculation_status": "SIZING_CALCULATION_COMPLETE",
        "workflow_status": "SIZING_CALCULATION_COMPLETE",
        "engineering_warnings": [
            "Nozzle IDs are hydraulically co-optimized within 1–3 m/s band only.",
            "PRELIMINARY_GEOMETRY_NOT_MECHANICALLY_VERIFIED on all sized nozzles.",
            "Assumption-based K scenarios are not owner-verified loss data.",
        ],
    }


def _failure_hints(
    scenario_results: dict[str, Any],
    constraints: dict[str, Any],
) -> list[str]:
    hints: list[str] = []
    if constraints.get("duty_constraint") == "NOT_SATISFIED":
        hints.append("THERMAL_DUTY_BELOW_TARGET")
    mid = scenario_results.get("mid_band") or {}
    tube_s = mid.get("tube_nozzle_solve") or {}
    shell_s = mid.get("shell_nozzle_solve") or {}
    if tube_s.get("status") == "NO_FEASIBLE_WITHIN_DESIGN_BOUNDS":
        hints.append("TUBE_FULL_PATH_BUDGET_EXCEEDED_BY_BUNDLE_AND_FIXED_LOCALS")
    if shell_s.get("status") == "NO_FEASIBLE_WITHIN_DESIGN_BOUNDS":
        mech = shell_s.get("failure_dominant_mechanism")
        hints.append(str(mech or "SHELL_FULL_PATH_BUDGET_EXCEEDED"))
    return hints


def render_nozzle_cooptimization_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# {report['TASK_ID']}",
        "",
        f"- Outcome: **{report['found_feasible_design']}**",
        f"- Recommended: `{report['recommendation']['recommended_candidate_id']}`",
        "",
        "## Candidates (mid_band scenario)",
        "",
        "| ID | Q kW | Area m² | Partial tube/shell Pa | Tube nozzle m / v | Shell nozzle m / v | Full path status |",
        "|---|---:|---:|---:|---|---:|---|",
    ]
    for row in report["sizing_candidates"]:
        if row["rating_participation_status"] != "FULLY_RATED":
            continue
        sc = row.get("loss_scenario_results", {}).get("mid_band") or {}
        therm = row["thermal_rating"]
        hyd = row["hydraulic_performance"]
        geom = row["geometry"]
        sel = sc.get("selected_nozzles") or {}
        q_kw = float(therm["duty_w"]) / 1000 if therm.get("duty_w") else None
        lines.append(
            f"| `{row['candidate_id'][:8]}` | {q_kw:.2f} | {geom.get('task171_rated_outside_area_m2')} | "
            f"{hyd.get('live_tube_dp_pa')}/{hyd.get('live_shell_dp_pa')} | "
            f"{sel.get('tube_side_inside_diameter_m')}/{sel.get('tube_side_velocity_m_s')} | "
            f"{sel.get('shell_side_inside_diameter_m')}/{sel.get('shell_side_velocity_m_s')} | "
            f"{sc.get('overall_scenario_status')} |"
        )
    lines.append("")
    lines.append("## K scenario summary")
    for row in report["sizing_candidates"]:
        if row["rating_participation_status"] != "FULLY_RATED":
            continue
        lines.append(f"- `{row['candidate_id'][:8]}`:")
        for key in LOSS_SCENARIO_KEYS:
            sc = row.get("loss_scenario_results", {}).get(key) or {}
            lines.append(f"  - {key}: {sc.get('overall_scenario_status')}")
    return "\n".join(lines) + "\n"


def write_nozzle_cooptimization_reports(
    report: dict[str, Any],
    output_dir: Path,
    *,
    basename: str = "R27C_NOZZLE_PRESSURE_BUDGET_COOPTIMIZATION",
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{basename}.json"
    md_path = output_dir / f"{basename}.md"
    json_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    md_path.write_text(render_nozzle_cooptimization_markdown(report), encoding="utf-8")
    return json_path, md_path
