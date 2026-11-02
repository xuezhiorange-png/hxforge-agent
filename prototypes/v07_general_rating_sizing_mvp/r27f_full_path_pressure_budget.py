"""R27F: full-path pressure budget, nozzle margin, and robustness on eight rated structures."""

# ruff: noqa: E501

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
    CandidateSelectionRecord,
    enumerate_experimental_rating_candidates,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.engineering_hydraulic_path_input_v1 import (
    R27B_ASSUMPTION_LOSS_COEFFICIENT_SCENARIOS,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_engineering_rating_core import (
    ENGINEERING_NUMERIC_VALID,
    run_experimental_engineering_rating,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_engineering_rating_live_bridge import (
    build_experimental_engineering_rating_live_package,
)
from prototypes.v07_general_rating_sizing_mvp.nozzle_pressure_budget_solver import (
    LossScenarioKey,
    _diameter_from_velocity_m,
    _shell_bd_internal_pa,
    _shell_external_dp_pa_for_nozzle_d,
    _side_inlet_density_kg_m3,
    _tube_path_dp_pa_for_nozzle_d,
    _velocity_bounds_m_s,
    cooptimize_nozzles_for_candidate_scenario,
)
from prototypes.v07_general_rating_sizing_mvp.positive_duty_cell import build_native_cell_context
from prototypes.v07_general_rating_sizing_mvp.r27e_reference_regression import (
    r27d_seven_reference_candidate_ids,
)

_TASK_ID = "V07_R27F_FULL_PATH_PRESSURE_BUDGET_AND_ROBUSTNESS"
_SCHEMA = "hxforge.r27f-full-path-pressure-budget.v27f"
_DESIGN_DUTY_W_MIN = 330_000.0
_SCENARIO_KEYS: tuple[LossScenarioKey, ...] = (
    "mid_band",
    "low_loss_sensitivity",
    "high_loss_sensitivity",
)
_RECOVERY_FULL_MESH_ID = "09dac82a-0a84-5bc2-9b3f-93aaecd30a9e"


def r27f_eight_full_mesh_candidate_ids(case: EngineeringCase) -> tuple[str, ...]:
    refs = r27d_seven_reference_candidate_ids(case)
    return refs + (_RECOVERY_FULL_MESH_ID,)


def _loss_band_label(key: LossScenarioKey) -> str:
    if key == "low_loss_sensitivity":
        return "low_loss"
    if key == "high_loss_sensitivity":
        return "high_loss"
    return "mid_band"


def evaluate_velocity_margin_curve(
    *,
    case: EngineeringCase,
    record: CandidateSelectionRecord,
    postpass: dict[str, Any],
    loss_scenario_key: LossScenarioKey,
    velocity_samples_m_s: tuple[float, ...] = (1.0, 1.5, 2.0, 2.5, 3.0),
) -> dict[str, Any]:
    """Independent margin study: full-path Δp at sampled nozzle velocities (both sides synced)."""
    scenario = R27B_ASSUMPTION_LOSS_COEFFICIENT_SCENARIOS[loss_scenario_key]
    max_tube = case.max_tube_side_pressure_drop_pa
    max_shell = case.max_shell_side_pressure_drop_pa
    v_min, v_max = _velocity_bounds_m_s()
    points: list[dict[str, Any]] = []
    for v in velocity_samples_m_s:
        if v < v_min - 1e-9 or v > v_max + 1e-9:
            continue
        tube_rho = _side_inlet_density_kg_m3(case, "tube_side")
        shell_rho = _side_inlet_density_kg_m3(case, "shell_side")
        tube_d = _diameter_from_velocity_m(
            mass_flow_kg_s=float(case.tube_side.mass_flow_kg_s),
            rho=tube_rho,
            velocity_m_s=v,
        )
        shell_d = _diameter_from_velocity_m(
            mass_flow_kg_s=float(case.shell_side.mass_flow_kg_s),
            rho=shell_rho,
            velocity_m_s=v,
        )
        tube_total, tube_bd = _tube_path_dp_pa_for_nozzle_d(
            case=case,
            record=record,
            postpass=postpass,
            scenario=scenario,
            tube_nozzle_d_m=Decimal(str(tube_d)),
        )
        shell_ext, shell_bd = _shell_external_dp_pa_for_nozzle_d(
            case=case,
            record=record,
            scenario=scenario,
            shell_nozzle_d_m=Decimal(str(shell_d)),
        )
        shell_int = _shell_bd_internal_pa(postpass)
        shell_total = None
        if shell_ext is not None and shell_int is not None:
            shell_total = shell_ext + shell_int
        tube_margin = float(max_tube - tube_total) if tube_total is not None else None
        shell_margin = float(max_shell - shell_total) if shell_total is not None else None
        points.append(
            {
                "velocity_m_s": v,
                "tube_nozzle_inside_diameter_m": tube_d,
                "shell_nozzle_inside_diameter_m": shell_d,
                "tube_full_path_dp_pa": str(tube_total) if tube_total else None,
                "shell_full_path_dp_pa": str(shell_total) if shell_total else None,
                "tube_margin_pa": tube_margin,
                "shell_margin_pa": shell_margin,
                "tube_breakdown_pa": {k: str(val) for k, val in tube_bd.items()},
                "shell_external_breakdown_pa": {k: str(val) for k, val in shell_bd.items()},
                "shell_bell_delaware_internal_dp_pa": (
                    str(shell_int) if shell_int is not None else None
                ),
            }
        )
    best_tube = max(
        (p for p in points if p.get("tube_margin_pa") is not None),
        key=lambda p: float(p["tube_margin_pa"]),
        default=None,
    )
    best_shell = max(
        (p for p in points if p.get("shell_margin_pa") is not None),
        key=lambda p: float(p["shell_margin_pa"]),
        default=None,
    )
    return {
        "loss_scenario_key": loss_scenario_key,
        "velocity_design_band_m_s": {"min": v_min, "max": v_max},
        "sample_points": points,
        "best_margin_in_band": {
            "tube_side": best_tube,
            "shell_side": best_shell,
        },
    }


def _extract_budget_row(
    *,
    coopt: dict[str, Any],
    case: EngineeringCase,
) -> dict[str, Any]:
    fp = coopt.get("full_path_hydraulic_verification") or {}
    tube_solve = coopt.get("tube_nozzle_solve") or {}
    shell_solve = coopt.get("shell_nozzle_solve") or {}
    tube_loc = (coopt.get("local_loss_breakdown_pa") or {}).get("tube_side") or {}
    shell_loc = (coopt.get("local_loss_breakdown_pa") or {}).get("shell_side") or {}
    max_tube = float(case.max_tube_side_pressure_drop_pa)
    max_shell = float(case.max_shell_side_pressure_drop_pa)

    def _f(key: str) -> float | None:
        raw = fp.get(key)
        if raw is None:
            return None
        return float(raw)

    tube_internal = float(tube_loc.get("tube_internal_friction_dp_pa", 0) or 0)
    tube_fixed_locals = sum(
        float(tube_loc.get(k, 0) or 0)
        for k in (
            "tube_channel_head_dp_pa",
            "tube_bundle_entrance_dp_pa",
            "tube_bundle_exit_dp_pa",
        )
    )
    tube_nozzle = float(tube_loc.get("tube_nozzle_pair_dp_pa", 0) or 0)
    shell_internal = float(shell_loc.get("shell_bell_delaware_internal_dp_pa", 0) or 0)
    shell_fixed = sum(
        float(shell_loc.get(k, 0) or 0)
        for k in (
            "shell_inlet_transition_dp_pa",
            "shell_outlet_transition_dp_pa",
        )
        if shell_loc.get(k) is not None
    )
    shell_nozzle = float(shell_loc.get("shell_nozzle_pair_dp_pa", 0) or 0)

    tube_full = _f("FULL_PATH_TUBE_TOTAL_DP_PA") or float(
        tube_loc.get("tube_modeled_full_path_dp_pa") or 0
    )
    shell_full = _f("FULL_PATH_SHELL_TOTAL_DP_PA") or (
        shell_internal + shell_fixed + shell_nozzle if shell_internal else None
    )

    return {
        "loss_scenario_key": coopt.get("loss_scenario_key"),
        "scenario_id": coopt.get("scenario_id"),
        "overall_scenario_status": coopt.get("overall_scenario_status"),
        "full_path_feasible": coopt.get("full_path_feasible"),
        "tube_side": {
            "internal_bundle_friction_dp_pa": tube_internal,
            "fixed_local_dp_pa": tube_fixed_locals,
            "nozzle_pair_local_dp_pa": tube_nozzle,
            "modeled_full_path_dp_pa": tube_full,
            "max_allowed_dp_pa": max_tube,
            "remaining_margin_pa": max_tube - tube_full if tube_full is not None else None,
            "nozzle_solve_status": tube_solve.get("status"),
            "selected_nozzle_d_m": tube_solve.get("selected_inside_diameter_m"),
            "selected_velocity_m_s": tube_solve.get("selected_velocity_m_s"),
            "dp_at_min_diameter_max_velocity_pa": tube_solve.get(
                "dp_at_min_diameter_max_velocity_pa"
            ),
            "dp_at_max_diameter_min_velocity_pa": tube_solve.get(
                "dp_at_max_diameter_min_velocity_pa"
            ),
            "dp_fixed_without_nozzle_pair_pa": tube_solve.get("dp_fixed_without_nozzle_pair_pa"),
            "dominant_mechanism": tube_solve.get("failure_dominant_mechanism"),
        },
        "shell_side": {
            "bell_delaware_internal_dp_pa": shell_internal,
            "fixed_transition_and_head_dp_pa": shell_fixed,
            "nozzle_pair_local_dp_pa": shell_nozzle,
            "modeled_full_path_dp_pa": shell_full,
            "max_allowed_dp_pa": max_shell,
            "remaining_margin_pa": (max_shell - shell_full if shell_full is not None else None),
            "nozzle_solve_status": shell_solve.get("status"),
            "selected_nozzle_d_m": shell_solve.get("selected_inside_diameter_m"),
            "selected_velocity_m_s": shell_solve.get("selected_velocity_m_s"),
            "dp_at_min_diameter_max_velocity_pa": shell_solve.get(
                "dp_at_min_diameter_max_velocity_pa"
            ),
            "dp_at_max_diameter_min_velocity_pa": shell_solve.get(
                "dp_at_max_diameter_min_velocity_pa"
            ),
            "dp_fixed_without_nozzle_pair_pa": shell_solve.get("dp_fixed_without_nozzle_pair_pa"),
            "dominant_mechanism": shell_solve.get("failure_dominant_mechanism"),
            "outside_velocity_band_note": shell_solve.get("OUTSIDE_DESIGN_VELOCITY_RANGE"),
        },
        "authorized_full_path": {
            "status": fp.get("status"),
            "FULL_PATH_HYDRAULIC_STATUS": fp.get("FULL_PATH_HYDRAULIC_STATUS"),
            "FULL_PATH_TUBE_CONSTRAINT_STATUS": fp.get("FULL_PATH_TUBE_CONSTRAINT_STATUS"),
            "FULL_PATH_SHELL_CONSTRAINT_STATUS": fp.get("FULL_PATH_SHELL_CONSTRAINT_STATUS"),
        },
    }


def _build_structure_recommendation(rows: list[dict[str, Any]]) -> dict[str, Any]:
    thermal_ok = [r for r in rows if r.get("thermal_status") == "SATISFIES_330KW"]
    nozzle_only_fixable = 0
    fixed_internal_block = 0
    shell_dominated = 0
    tube_dominated = 0
    for row in thermal_ok:
        for sc in row.get("scenario_budgets") or []:
            shell = sc.get("shell_side") or {}
            tube = sc.get("tube_side") or {}
            fixed_shell = shell.get("dp_fixed_without_nozzle_pair_pa")
            fixed_tube = tube.get("dp_fixed_without_nozzle_pair_pa")
            max_shell = shell.get("max_allowed_dp_pa")
            max_tube = tube.get("max_allowed_dp_pa")
            if fixed_shell and max_shell and float(fixed_shell) > float(max_shell):
                fixed_internal_block += 1
                shell_dominated += 1
            elif fixed_tube and max_tube and float(fixed_tube) > float(max_tube):
                fixed_internal_block += 1
                tube_dominated += 1
            elif sc.get("full_path_feasible"):
                nozzle_only_fixable += 1
            margin_curve = row.get("margin_curves") or {}
            mid = margin_curve.get("mid_band") or {}
            best = (mid.get("best_margin_in_band") or {}).get("shell_side") or {}
            if best.get("shell_margin_pa") is not None and float(best["shell_margin_pa"]) < 1.0:
                pass  # critical margin counted per candidate in row

    can_nozzle_only = fixed_internal_block == 0 and any(
        r.get("any_full_path_feasible") for r in thermal_ok
    )
    return {
        "can_achieve_meaningful_margin_by_nozzle_alone": can_nozzle_only,
        "structures_with_fixed_internal_exceeding_budget": fixed_internal_block,
        "shell_side_internal_dominance_count": shell_dominated,
        "tube_side_fixed_local_dominance_count": tube_dominated,
        "priority_if_nozzle_insufficient": (
            "Reduce shell-side Bell-Delaware bundle Δp (baffle spacing, shell ID, tube count) "
            "before tube-side friction — shell fixed+internal failures dominate 09dac82a and "
            "near-limit low_loss cases."
            if shell_dominated >= tube_dominated
            else "Reduce tube-side bundle friction and fixed channel/bundle K losses."
        ),
        "authorized_geometry_levers": [
            "baffle_spacing_m (shell Δp, may reduce duty)",
            "physical_tube_count / shell_inside_diameter_m (area & shell flow)",
            "tube_length_m (tube friction, duty)",
        ],
        "next_local_search_suggestion": (
            "Pareto on shell_inside_diameter_m × baffle_spacing_m at fixed Task174-ready "
            "envelope, mid_band K only, skipping 0.65 m transition-blocked family."
        ),
    }


def analyze_candidate_full_path(
    *,
    case: EngineeringCase,
    record: CandidateSelectionRecord,
    postpass: dict[str, Any],
    n4_duty_w: float | None,
) -> dict[str, Any]:
    thermal_status = (
        "SATISFIES_330KW"
        if n4_duty_w is not None and n4_duty_w >= _DESIGN_DUTY_W_MIN
        else "BELOW_330KW"
    )
    scenario_budgets: list[dict[str, Any]] = []
    margin_curves: dict[str, Any] = {}
    any_feasible = False
    for key in _SCENARIO_KEYS:
        coopt = cooptimize_nozzles_for_candidate_scenario(
            case=case,
            record=record,
            postpass=postpass,
            loss_scenario_key=key,
        )
        scenario_budgets.append(_extract_budget_row(coopt=coopt, case=case))
        if coopt.get("full_path_feasible"):
            any_feasible = True
        margin_curves[key] = evaluate_velocity_margin_curve(
            case=case,
            record=record,
            postpass=postpass,
            loss_scenario_key=key,
        )

    low = next(s for s in scenario_budgets if s["loss_scenario_key"] == "low_loss_sensitivity")
    shell_low_margin = (low.get("shell_side") or {}).get("remaining_margin_pa")

    return {
        "candidate_id": record.candidate_id,
        "candidate_id_prefix": record.candidate_id[:8],
        "geometry": {
            "shell_inside_diameter_m": record.shell_inside_diameter_m,
            "tube_length_m": record.tube_length_m,
            "baffle_spacing_m": record.baffle_spacing_m,
            "physical_tube_count": record.physical_tube_count,
        },
        "n4_duty_w": n4_duty_w,
        "thermal_status": thermal_status,
        "internal_hydraulic_partial": {
            "tube_dp_pa": postpass.get("recalculated_tube_dp_pa"),
            "shell_dp_pa": postpass.get("recalculated_shell_dp_pa"),
            "tube_dp_constraint": postpass.get("tube_dp_constraint"),
            "shell_dp_constraint": postpass.get("shell_dp_constraint"),
        },
        "scenario_budgets": scenario_budgets,
        "margin_curves": margin_curves,
        "any_full_path_feasible": any_feasible,
        "low_loss_shell_margin_at_min_nozzle_pa": shell_low_margin,
        "loss_band_feasibility": {
            _loss_band_label(s["loss_scenario_key"]): s.get("full_path_feasible")
            for s in scenario_budgets
        },
    }


def load_rating_postpass_for_candidate(
    case: EngineeringCase,
    *,
    candidate_id: str,
    selection: Any,
    mesh_result_cache: dict[int, Any] | None = None,
) -> tuple[dict[str, Any], float | None, str | None]:
    native = build_native_cell_context(case, selection=selection, candidate_id=candidate_id)
    cache: dict[int, Any] = mesh_result_cache if mesh_result_cache is not None else {}
    n1 = run_experimental_engineering_rating(
        case, subdivisions=1, native=native, mesh_result_cache=cache
    )
    if n1.status != ENGINEERING_NUMERIC_VALID:
        return {}, None, n1.failure_code
    package = build_experimental_engineering_rating_live_package(
        case,
        native=native,
        run_mesh_ladder=True,
        run_hydraulic_sensitivity=False,
        mesh_result_cache=cache,
    )
    mesh = package.get("mesh_convergence") or {}
    if mesh.get("FULL_RATING_CONVERGED") is not True:
        return {}, None, "FULL_RATING_NOT_CONVERGED"
    postpass = package.get("live_thermal_state_hydraulic_postpass") or {}
    receipt = package.get("engineering_delivery_receipt") or {}
    duty = receipt.get("N4_DUTY_W")
    duty_f = float(duty) if duty is not None else None
    return postpass, duty_f, None


def run_r27f_full_path_pressure_budget(
    case: EngineeringCase,
    *,
    candidate_ids: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    selection = enumerate_experimental_rating_candidates(
        case,
        rating_selection_policy="r27d",
        rate_all_distinct_task174_ready=True,
    )
    ids = candidate_ids or r27f_eight_full_mesh_candidate_ids(case)
    rows: list[dict[str, Any]] = []
    for cid in ids:
        postpass, duty, err = load_rating_postpass_for_candidate(
            case, candidate_id=cid, selection=selection
        )
        record = next(r for r in selection.records if r.candidate_id == cid)
        if err:
            rows.append(
                {
                    "candidate_id": cid,
                    "candidate_id_prefix": cid[:8],
                    "error": err,
                    "thermal_status": "NOT_RATED",
                }
            )
            continue
        rows.append(
            analyze_candidate_full_path(
                case=case,
                record=record,
                postpass=postpass,
                n4_duty_w=duty,
            )
        )
    recommendation = _build_structure_recommendation(rows)
    return {
        "schema_version": _SCHEMA,
        "TASK_ID": _TASK_ID,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "upstream_head": "9795e1839658690118848f3123660b7dcee3e9f2",
        "design_duty_w_min": _DESIGN_DUTY_W_MIN,
        "candidate_count": len(ids),
        "candidates": rows,
        "k_scenario_sensitivity_summary": {
            "scenarios": list(_SCENARIO_KEYS),
            "feasible_counts": {
                key: sum(
                    1
                    for r in rows
                    if (r.get("loss_band_feasibility") or {}).get(_loss_band_label(key))
                )
                for key in _SCENARIO_KEYS
            },
        },
        "structure_optimization_recommendation": recommendation,
    }


def write_r27f_reports(report: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "R27F_FULL_PATH_PRESSURE_BUDGET.json"
    md_path = output_dir / "R27F_FULL_PATH_PRESSURE_BUDGET.md"
    json_path.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    lines = [
        f"# R27F full-path pressure budget ({report['TASK_ID']})",
        "",
        f"Generated: {report['generated_at_utc']}",
        "",
        "## Verdict",
        "",
        f"- Meaningful margin by nozzle alone: "
        f"**{report['structure_optimization_recommendation']['can_achieve_meaningful_margin_by_nozzle_alone']}**",
        f"- Priority: {report['structure_optimization_recommendation']['priority_if_nozzle_insufficient']}",
        "",
    ]
    for row in report.get("candidates") or []:
        if row.get("error"):
            lines.append(f"## {row['candidate_id_prefix']} — ERROR {row['error']}")
            continue
        lines.append(f"## {row['candidate_id_prefix']} — {row['thermal_status']}")
        lines.append(f"- N4 Q: {row.get('n4_duty_w')} W")
        lines.append(f"- Full-path feasible any K: {row.get('any_full_path_feasible')}")
        for sc in row.get("scenario_budgets") or []:
            ts = sc.get("tube_side") or {}
            ss = sc.get("shell_side") or {}
            lines.append(
                f"- **{sc['loss_scenario_key']}**: tube margin {ts.get('remaining_margin_pa')} Pa, "
                f"shell margin {ss.get('remaining_margin_pa')} Pa, feasible={sc.get('full_path_feasible')}"
            )
        lines.append("")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path
