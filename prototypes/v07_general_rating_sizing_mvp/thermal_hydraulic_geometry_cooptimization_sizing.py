"""R27D: thermal–hydraulic–geometry co-optimization (design → structure → rating → full path)."""

# ruff: noqa: E501

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from prototypes.v07_general_rating_sizing_mvp.calculation_first_automatic_sizing import (
    _constraint_summary,
    _geometry_report_block,
    estimate_preliminary_nozzle_diameters,
    find_candidate_b_record,
    find_middle_reference_record,
)
from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
    CandidateSelectionOutcome,
    CandidateSelectionRecord,
    enumerate_experimental_rating_candidates,
    selection_to_json,
)
from prototypes.v07_general_rating_sizing_mvp.case_streams import design_conditions_for_report
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.engineering_hydraulic_path_input_v1 import (
    R27B_ASSUMPTION_LOSS_COEFFICIENT_SCENARIOS,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_multi_candidate_engineering_sizing import (
    run_experimental_multi_candidate_engineering_sizing,
)
from prototypes.v07_general_rating_sizing_mvp.full_path_constraint_aware_sizing import (
    REFERENCE_GEOMETRY_FINGERPRINTS,
    find_short_reference_record,
)
from prototypes.v07_general_rating_sizing_mvp.nozzle_cooptimization_sizing import (
    LOSS_SCENARIO_KEYS,
    _scenario_recommendation_eligible,
    _thermal_block_from_row,
)
from prototypes.v07_general_rating_sizing_mvp.nozzle_pressure_budget_solver import (
    LossScenarioKey,
    cooptimize_nozzles_for_candidate_scenario,
)

_TASK_ID = "V07_R27D_THERMAL_HYDRAULIC_GEOMETRY_CO_OPTIMIZATION"
_SCHEMA = "hxforge.thermal-hydraulic-geometry-cooptimization.v27d"
_SIZING_AUTHORITY = "EXPERIMENTAL_CALCULATION_FIRST_NOT_PRODUCTION_APPROVED"


def _phase_a_screening(
    record: CandidateSelectionRecord,
    *,
    target_duty_w: Decimal,
) -> dict[str, Any]:
    if not record.structural_admitted:
        return {
            "phase_a_status": "STRUCTURAL_BLOCKED",
            "task168_chain_status": record.task168_chain_status,
            "blocked_stage": record.task168_blocked_stage,
            "blocked_codes": list(record.task168_blocked_codes),
            "disclosure": "Structural admission failed; not queued for mesh rating.",
        }
    if record.task168_chain_status == "BLOCKED_DOWNSTREAM":
        return {
            "phase_a_status": "TASK168_CHAIN_BLOCKED",
            "blocked_stage": record.task168_blocked_stage,
            "blocked_codes": list(record.task168_blocked_codes),
            "disclosure": "Task168 chain blocked; not queued for mesh rating.",
        }
    if not record.rating_request_ready:
        return {
            "phase_a_status": "TASK174_NOT_READY",
            "task174_status": record.task174_status,
            "disclosure": "Task174 validation did not produce a rating-ready request.",
        }
    hints: list[str] = []
    area = Decimal(record.nominal_tube_outer_area_proxy_m2 or "0")
    if area <= 0:
        hints.append("NOMINAL_AREA_PROXY_NON_POSITIVE")
    return {
        "phase_a_status": "ELIGIBLE_FOR_FORMAL_RATING",
        "nominal_tube_outer_area_proxy_m2": record.nominal_tube_outer_area_proxy_m2,
        "physical_tube_count": record.physical_tube_count,
        "task025_total_parallel_flow_area_m2": record.task025_total_parallel_flow_area_m2,
        "shell_inside_diameter_m": record.shell_inside_diameter_m,
        "screening_hints": hints,
        "target_duty_w": str(target_duty_w),
        "disclosure": (
            "Phase A uses Task168/171/174 enumeration outputs only; it does not eliminate "
            "candidates from the formal rating queue and does not treat N1 screen failure as "
            "permanent rejection."
        ),
    }


def _internal_hydraulic_satisfied(constraints: dict[str, Any]) -> bool:
    return (
        constraints.get("tube_dp_constraint") == "SATISFIED"
        and constraints.get("shell_dp_constraint") == "SATISFIED"
        and constraints.get("hydraulic_constraint_status") == "SATISFIED"
    )


def _r27d_formal_feasible(row: dict[str, Any], scenario_key: LossScenarioKey) -> bool:
    return _scenario_recommendation_eligible(row, scenario_key)


def _pareto_mid_band_feasible(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    feasible = [row for row in rows if _r27d_formal_feasible(row, "mid_band")]
    points: list[tuple[dict[str, Any], Decimal, Decimal]] = []
    for row in feasible:
        geom = row.get("geometry") or {}
        area_raw = geom.get("task171_rated_outside_area_m2")
        if area_raw is None:
            continue
        sc = row["loss_scenario_results"]["mid_band"]
        fp = sc.get("full_path_hydraulic_verification") or {}
        tube_m = fp.get("TUBE_FULL_PATH_DP_MARGIN_PA")
        shell_m = fp.get("SHELL_FULL_PATH_DP_MARGIN_PA")
        if tube_m is None or shell_m is None:
            continue
        min_margin = min(Decimal(str(tube_m)), Decimal(str(shell_m)))
        points.append((row, Decimal(str(area_raw)), min_margin))

    pareto: list[dict[str, Any]] = []
    for row, area, margin in points:
        dominated = False
        for _other, area_b, margin_b in points:
            if area_b <= area and margin_b >= margin and (area_b < area or margin_b > margin):
                dominated = True
                break
        if not dominated:
            pareto.append(
                {
                    "candidate_id": row["candidate_id"],
                    "task171_rated_outside_area_m2": str(area),
                    "mid_band_min_full_path_dp_margin_pa": str(margin),
                    "tube_side_nozzle_inside_diameter_m": (
                        row["loss_scenario_results"]["mid_band"]
                        .get("selected_nozzles", {})
                        .get("tube_side_inside_diameter_m")
                    ),
                    "shell_side_nozzle_inside_diameter_m": (
                        row["loss_scenario_results"]["mid_band"]
                        .get("selected_nozzles", {})
                        .get("shell_side_inside_diameter_m")
                    ),
                }
            )
    pareto.sort(
        key=lambda item: (Decimal(item["task171_rated_outside_area_m2"]), item["candidate_id"])
    )
    return pareto


def _pick_recommended(pareto: list[dict[str, Any]]) -> str | None:
    if not pareto:
        return None
    best = max(
        pareto,
        key=lambda item: (
            Decimal(item["mid_band_min_full_path_dp_margin_pa"]),
            -Decimal(item["task171_rated_outside_area_m2"]),
        ),
    )
    return str(best["candidate_id"])


def classify_r27d_search_phases(
    *,
    candidate_space_count: int,
    task174_ready_count: int,
    distinct_task174_ready_geometry_count: int,
    selected_for_full_mesh_rating_count: int,
    full_mesh_rating_completed_count: int,
    full_path_feasible_mid_band_among_fully_rated: int,
    solver_budget_prevented_selecting_all_ready: bool,
) -> dict[str, str]:
    """Deterministic search-phase labels (unit-testable, no solver rerun)."""
    phases: dict[str, str] = {}
    phases["enumeration"] = (
        "ENUMERATION_COMPLETE" if candidate_space_count > 0 else "ENUMERATION_NOT_RUN"
    )
    if solver_budget_prevented_selecting_all_ready:
        phases["ready_geometry_selection"] = "PARTIAL_READY_GEOMETRY_SELECTION"
    elif selected_for_full_mesh_rating_count >= distinct_task174_ready_geometry_count:
        phases["ready_geometry_selection"] = "ALL_READY_GEOMETRIES_SELECTED"
    else:
        phases["ready_geometry_selection"] = "PARTIAL_READY_GEOMETRY_SELECTION"
    if selected_for_full_mesh_rating_count == 0:
        phases["full_mesh_rating"] = "FULL_MESH_RATING_NOT_STARTED"
    elif full_mesh_rating_completed_count >= selected_for_full_mesh_rating_count:
        phases["full_mesh_rating"] = "FULL_MESH_RATING_COMPLETE"
    else:
        phases["full_mesh_rating"] = "FULL_MESH_RATING_INCOMPLETE"
    if full_mesh_rating_completed_count == 0:
        phases["feasibility_among_fully_rated"] = "NO_FULL_MESH_RATING_TO_EVALUATE"
    elif full_path_feasible_mid_band_among_fully_rated > 0:
        phases["feasibility_among_fully_rated"] = "CONFIRMED_FEASIBLE_PRESENT_MID_BAND"
    else:
        phases["feasibility_among_fully_rated"] = "NO_CONFIRMED_FEASIBLE_AMONG_EVALUATED_CANDIDATES"
    return phases


def _mesh_rating_evidence_from_multi_row(row: dict[str, Any]) -> dict[str, Any]:
    screening = row.get("screening_n1_status") or ""
    n1_status = row.get("n1_thermal_numeric_status")
    participation = row.get("rating_participation_status")
    full_converged = row.get("FULL_RATING_CONVERGED") is True
    entered_mesh_ladder = full_converged or (
        participation == "FULLY_RATED"
        or (
            participation in {"FULLY_RATED", "SCREENED_N1_ONLY"}
            and screening not in ("NOT_SELECTED_FOR_RATING",)
            and n1_status == "ENGINEERING_NUMERIC_VALID"
        )
    )
    if full_converged:
        outcome = "FULL_MESH_RATING_CONVERGED"
        classification = "FULL_MESH_COMPLETE"
    elif n1_status != "ENGINEERING_NUMERIC_VALID":
        outcome = "N1_THERMAL_SCREEN_BLOCKED"
        classification = "NUMERIC_OR_INPUT_BLOCK_AT_N1"
    elif participation == "SCREENED_N1_ONLY":
        outcome = "MESH_LADDER_RAN_WITHOUT_FULL_RATING_CONVERGENCE"
        classification = "MESH_LADDER_DID_NOT_CONVERGE"
    else:
        outcome = "NOT_SELECTED_OR_NOT_EVALUATED"
        classification = "NOT_FORMALLY_RATED_THIS_RUN"
    return {
        "rating_participation_status": participation,
        "task174_status": row.get("task174_status"),
        "screening_n1_status": screening,
        "n1_thermal_numeric_status": n1_status,
        "n1_failure_code": (
            screening.replace("BLOCKED_N1_", "") if screening.startswith("BLOCKED_N1_") else None
        ),
        "n1_duty_w": row.get("n1_duty_w"),
        "entered_n2_n4_mesh_ladder": entered_mesh_ladder
        and n1_status == "ENGINEERING_NUMERIC_VALID",
        "full_rating_converged": full_converged,
        "mesh_rating_outcome": outcome,
        "mesh_rating_classification": classification,
        "disclosure": (
            "N1 thermal screen failure does not classify the candidate as thermally or "
            "full-path infeasible—only that full mesh rating was not completed."
        ),
    }


def _search_coverage_block(
    selection: CandidateSelectionOutcome,
    multi: dict[str, Any],
    sizing_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    distinct_ready = len(
        {r.geometry_projection_hash for r in selection.records if r.rating_request_ready}
    )
    selected = len(selection.selected_candidate_ids)
    fully_rated = sum(
        1 for row in sizing_rows if row.get("rating_participation_status") == "FULLY_RATED"
    )
    duty_ok = sum(
        1
        for row in sizing_rows
        if (row.get("constraints") or {}).get("duty_constraint") == "SATISFIED"
    )
    internal_ok = sum(
        1 for row in sizing_rows if _internal_hydraulic_satisfied(row.get("constraints") or {})
    )
    full_path_ok = sum(
        1
        for row in sizing_rows
        if (row.get("loss_scenario_results") or {}).get("mid_band", {}).get("full_path_feasible")
    )
    full_path_among_fully_rated = sum(
        1
        for row in sizing_rows
        if row.get("rating_participation_status") == "FULLY_RATED"
        and (row.get("loss_scenario_results") or {}).get("mid_band", {}).get("full_path_feasible")
    )
    selected_incomplete = selected - fully_rated
    task174_not_ready = selection.candidate_space_count - selection.task174_ready_count
    solver_budget_incomplete = selected < distinct_ready
    phases = classify_r27d_search_phases(
        candidate_space_count=selection.candidate_space_count,
        task174_ready_count=selection.task174_ready_count,
        distinct_task174_ready_geometry_count=distinct_ready,
        selected_for_full_mesh_rating_count=selected,
        full_mesh_rating_completed_count=fully_rated,
        full_path_feasible_mid_band_among_fully_rated=full_path_among_fully_rated,
        solver_budget_prevented_selecting_all_ready=solver_budget_incomplete,
    )
    if solver_budget_incomplete:
        headline_status = "SEARCH_INCOMPLETE"
        headline_reason = f"Solver budget selected {selected} of {distinct_ready} Task174-ready distinct geometries."
    elif fully_rated < selected:
        headline_status = "FULL_MESH_RATING_INCOMPLETE"
        headline_reason = (
            f"{selected_incomplete} of {selected} selected candidates did not reach "
            "FULL_RATING_CONVERGED on the N1/N2/N4 mesh ladder."
        )
    else:
        headline_status = "FULL_MESH_RATING_COMPLETE"
        headline_reason = None
    return {
        "enumerated_candidate_space_count": selection.candidate_space_count,
        "structurally_admitted_count": selection.structurally_admitted_count,
        "task174_ready_count": selection.task174_ready_count,
        "task174_not_ready_combination_count": task174_not_ready,
        "distinct_task174_ready_geometry_count": distinct_ready,
        "selected_for_full_mesh_rating_count": selected,
        "selected_but_full_mesh_incomplete_count": selected_incomplete,
        "full_mesh_rating_completed_count": fully_rated,
        "duty_satisfied_count": duty_ok,
        "internal_hydraulic_satisfied_count": internal_ok,
        "full_path_feasible_mid_band_count": full_path_ok,
        "full_path_feasible_mid_band_among_fully_rated_count": full_path_among_fully_rated,
        "search_status": headline_status,
        "search_incomplete_reason": headline_reason,
        "search_phases": phases,
        "multi_candidate_summary": {
            "SCREENED_CANDIDATE_COUNT": multi.get("SCREENED_CANDIDATE_COUNT"),
            "FULLY_RATED_CANDIDATE_COUNT": multi.get("FULLY_RATED_CANDIDATE_COUNT"),
        },
        "disclosure": (
            "ALL_READY_GEOMETRIES_SELECTED means every Task174-ready distinct geometry was "
            "queued for mesh rating—not that every queued geometry completed full mesh rating. "
            "Task174-not-ready combinations are counted separately from selected-but-incomplete mesh runs. "
            "N1 screen failure is a rating-completion blocker, not a formal thermal or full-path verdict."
        ),
    }


def run_thermal_hydraulic_geometry_cooptimization(
    case: EngineeringCase,
    *,
    rate_all_distinct_task174_ready: bool = True,
    max_candidates_to_rate_override: int | None = None,
    run_full_mesh_hydraulic: bool = True,
    precomputed_selection: CandidateSelectionOutcome | None = None,
) -> dict[str, Any]:
    target_duty = Decimal(str(case.target_duty_w))
    selection = precomputed_selection
    if selection is None:
        selection = enumerate_experimental_rating_candidates(
            case,
            rating_selection_policy="r27d",
            max_candidates_to_rate_override=max_candidates_to_rate_override,
            rate_all_distinct_task174_ready=rate_all_distinct_task174_ready,
        )
    multi = run_experimental_multi_candidate_engineering_sizing(
        case,
        precomputed_selection=selection,
        run_full_mesh_hydraulic=run_full_mesh_hydraulic,
    )
    multi_by_id = {row["candidate_id"]: row for row in multi["candidates"]}
    rate_id_set = set(selection.selected_candidate_ids)

    sizing_rows: list[dict[str, Any]] = []
    for record in selection.records:
        phase_a = _phase_a_screening(record, target_duty_w=target_duty)
        row = multi_by_id.get(record.candidate_id)
        if row is None:
            continue
        geometry = _geometry_report_block(row=row, case=case)
        thermal = _thermal_block_from_row(row, case=case)
        constraints = _constraint_summary(row, target_duty_w=target_duty)
        scenario_results: dict[str, Any] = {}
        if (
            record.candidate_id in rate_id_set
            and row.get("FULL_RATING_CONVERGED") is True
            and row.get("rating_participation_status") == "FULLY_RATED"
        ):
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
                "mesh_rating_evidence": _mesh_rating_evidence_from_multi_row(row),
                "phase_a_screening": phase_a,
                "geometry": geometry,
                "thermal_rating": thermal,
                "hydraulic_performance": {
                    "live_tube_dp_pa": row.get("LIVE_TUBE_DP_PA"),
                    "live_shell_dp_pa": row.get("LIVE_SHELL_DP_PA"),
                    "tube_dp_margin_pa": row.get("TUBE_DP_MARGIN_PA"),
                    "shell_dp_margin_pa": row.get("SHELL_DP_MARGIN_PA"),
                    "hydraulic_dp_breakdown": row.get("hydraulic_dp_breakdown"),
                    "internal_hydraulic_satisfied": _internal_hydraulic_satisfied(constraints),
                },
                "constraints": constraints,
                "loss_scenario_results": scenario_results,
                "formal_feasibility_mid_band": _r27d_formal_feasible(
                    {
                        "rating_participation_status": row.get("rating_participation_status"),
                        "thermal_rating": thermal,
                        "constraints": constraints,
                        "loss_scenario_results": scenario_results,
                    },
                    "mid_band",
                ),
            }
        )

    pareto = _pareto_mid_band_feasible(sizing_rows)
    recommended_id = _pick_recommended(pareto)
    found = (
        "FOUND_FULL_PATH_FEASIBLE_DESIGN" if recommended_id else "NO_FULL_PATH_FEASIBLE_CANDIDATE"
    )
    coverage = _search_coverage_block(selection, multi, sizing_rows)

    refs: dict[str, Any] = {}
    baseline = find_candidate_b_record(selection)
    middle = find_middle_reference_record(selection)
    short = find_short_reference_record(selection)
    if baseline:
        refs["candidate_b_baseline_id"] = baseline.candidate_id
    if middle:
        refs["middle_3_5m_reference_id"] = middle.candidate_id
    if short:
        refs["short_reference_id"] = short.candidate_id

    return {
        "schema_version": _SCHEMA,
        "TASK_ID": _TASK_ID,
        "generated_at_utc": datetime.now(tz=UTC).isoformat(),
        "PRODUCTION_DESIGN_APPROVED": False,
        "ENGINEERING_SIZING_ELIGIBILITY": "ASSUMPTION_BASED_NOT_ENGINEERING_SIZING_ELIGIBLE",
        "SIZING_AUTHORITY": _SIZING_AUTHORITY,
        "user_design_input": design_conditions_for_report(case),
        "preliminary_nozzle_sizing_reference": estimate_preliminary_nozzle_diameters(case),
        "loss_coefficient_scenarios": {
            key: {
                "scenario_id": val["scenario_id"],
                "disclosure": val["disclosure"],
                "ASSUMPTION_BASED": True,
            }
            for key, val in R27B_ASSUMPTION_LOSS_COEFFICIENT_SCENARIOS.items()
        },
        "candidate_selection": selection_to_json(selection),
        "search_coverage": coverage,
        "recommendation": {
            "recommended_candidate_id": recommended_id,
            "recommendation_basis": "MID_BAND_FULL_PATH_FEASIBLE_PARETO_THEN_MAX_HYDRAULIC_MARGIN",
            "pareto_mid_band_full_path_feasible": pareto,
            "low_loss_sensitivity_note": (
                "Candidate 9c4b84db-a0f6-58bb-b81c-3edffed9035a may appear under "
                "per_scenario_feasible_candidate_ids for low_loss_sensitivity only; "
                "shell full-path margin ~0.0005 Pa is numerical edge tolerance—not robust engineering margin."
            ),
            "per_scenario_feasible_candidate_ids": {
                key: [row["candidate_id"] for row in sizing_rows if _r27d_formal_feasible(row, key)]
                for key in LOSS_SCENARIO_KEYS
            },
            "reference_geometry_fingerprints": list(REFERENCE_GEOMETRY_FINGERPRINTS),
            "reference_candidate_ids": refs,
        },
        "sizing_candidates": sizing_rows,
        "found_feasible_design": found,
        "sizing_calculation_status": "SIZING_CALCULATION_COMPLETE",
        "workflow_status": "SIZING_CALCULATION_COMPLETE",
        "engineering_warnings": [
            "Joint optimization reuses experimental Task168–174 enumeration and mesh rating authority.",
            "Nozzle co-optimization is assumption-based K scenarios within 1–3 m/s only.",
            "Mechanical clearance and tubesheet layout are not verified.",
            "Full mesh rating incomplete among selected candidates does not prove design-space infeasibility.",
            "low_loss_sensitivity-only feasibility with ~0.0005 Pa shell margin is numerically critical, not robust.",
        ],
    }


def render_r27d_markdown(report: dict[str, Any]) -> str:
    title = "HXForge 330 kW 换热器自动联合选型结果"
    cov = report["search_coverage"]
    phases = cov.get("search_phases") or {}
    lines = [
        f"# {title}",
        "",
        f"**TASK_ID:** {report['TASK_ID']}",
        "",
        f"- 结论: **{report['found_feasible_design']}**",
        f"- 推荐候选: `{report['recommendation']['recommended_candidate_id']}`",
        f"- 搜索 headline: **{cov['search_status']}**",
        f"- 阶段: 枚举 `{phases.get('enumeration')}` | Ready 选中 `{phases.get('ready_geometry_selection')}` | "
        f"全网格 `{phases.get('full_mesh_rating')}` | 已评估可行 `{phases.get('feasibility_among_fully_rated')}`",
        f"- 选中/完成全网格: {cov['selected_for_full_mesh_rating_count']}/"
        f"{cov['full_mesh_rating_completed_count']} "
        f"（未完成 {cov.get('selected_but_full_mesh_incomplete_count', 0)}）",
        f"- Task174 未 Ready 组合（与选中队列分开）: {cov.get('task174_not_ready_combination_count', '—')}",
        "",
        "## 搜索覆盖",
        "",
        f"- 枚举空间: {cov['enumerated_candidate_space_count']}",
        f"- Task174 Ready: {cov['task174_ready_count']}",
        f"- 全网格 Rating 完成: {cov['full_mesh_rating_completed_count']}",
        f"- 热负荷满足: {cov['duty_satisfied_count']}",
        f"- 内部水力满足: {cov['internal_hydraulic_satisfied_count']}",
        f"- 完整流路 mid_band 可行: {cov['full_path_feasible_mid_band_count']}",
        "",
        "## Pareto (mid_band 完整流路可行: 面积 vs 最小裕量 Pa)",
        "",
    ]
    for item in report["recommendation"]["pareto_mid_band_full_path_feasible"]:
        lines.append(
            f"- `{item['candidate_id'][:8]}` area={item['task171_rated_outside_area_m2']} m² "
            f"min_margin={item['mid_band_min_full_path_dp_margin_pa']} Pa"
        )
    if not report["recommendation"]["pareto_mid_band_full_path_feasible"]:
        lines.append("- _(无可行 Pareto 点)_")
    lines.extend(["", "## 候选摘要 (mid_band)", ""])
    for row in report["sizing_candidates"]:
        if row["rating_participation_status"] != "FULLY_RATED":
            continue
        sc = row.get("loss_scenario_results", {}).get("mid_band") or {}
        geom = row["geometry"]
        therm = row["thermal_rating"]
        hyd = row["hydraulic_performance"]
        cons = row["constraints"]
        sel = sc.get("selected_nozzles") or {}
        q = float(therm["duty_w"]) / 1000 if therm.get("duty_w") else None
        lines.append(
            f"### `{row['candidate_id'][:8]}` "
            f"shell={geom.get('shell_inside_diameter_m')} m L={geom.get('tube_length_m')} m "
            f"Nt={geom.get('physical_tube_count')}"
        )
        lines.append(
            f"- Q={q:.2f} kW ({cons.get('duty_constraint')}); "
            f"面积={geom.get('task171_rated_outside_area_m2')} m²; "
            f"内部 Δp 管/壳={hyd.get('live_tube_dp_pa')}/{hyd.get('live_shell_dp_pa')} Pa; "
            f"完整流路={sc.get('overall_scenario_status')}"
        )
        lines.append(
            f"- 接管 管 D={sel.get('tube_side_inside_diameter_m')} m v={sel.get('tube_side_velocity_m_s')} m/s; "
            f"壳 D={sel.get('shell_side_inside_diameter_m')} v={sel.get('shell_side_velocity_m_s')} m/s"
        )
        lines.append("")
    return "\n".join(lines) + "\n"


def write_r27d_reports(
    report: dict[str, Any],
    output_dir: Path,
    *,
    basename: str = "R27D_THERMAL_HYDRAULIC_GEOMETRY_COOPTIMIZATION",
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{basename}.json"
    md_path = output_dir / f"{basename}.md"
    json_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    md_path.write_text(render_r27d_markdown(report), encoding="utf-8")
    return json_path, md_path
