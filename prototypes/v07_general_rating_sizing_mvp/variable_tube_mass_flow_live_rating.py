"""R18: baseline vs variable tube mass flow live n=1 rating comparison."""

# ruff: noqa: E501

from __future__ import annotations

import json
import time
from decimal import Decimal
from pathlib import Path
from typing import Any

from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
    enumerate_experimental_rating_candidates,
)
from prototypes.v07_general_rating_sizing_mvp.case_streams import tube_stream_spec
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.live_multi_mesh_rating import (
    PINNED_R16_CANDIDATE_ID,
    attach_live_hydraulic_postpass_for_mesh,
    build_live_multi_mesh_analysis,
    run_mesh_levels_for_candidate,
)
from prototypes.v07_general_rating_sizing_mvp.positive_duty_cell import build_native_cell_context


def _mesh_summary(row: dict[str, Any], postpass: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "tube_mass_flow_kg_s": (postpass or {}).get("tube_mass_flow_kg_s"),
        "shell_mass_flow_kg_s": (postpass or {}).get("shell_mass_flow_kg_s") or "20.000000",
        "duty_w": row.get("total_duty_w"),
        "tube_outlet_temperature_k": row.get("tube_outlet_temperature_k"),
        "shell_outlet_temperature_k": row.get("shell_outlet_temperature_k"),
        "energy_balance_residual_w": row.get("energy_balance_residual_w"),
        "rating_status": row.get("mesh_status") or row.get("status"),
        "task172_local_evaluation_count": row.get("task172_local_evaluation_count"),
        "wall_seconds": row.get("wall_seconds"),
        "tube_reynolds_number": (postpass or {}).get("tube_reynolds_number"),
        "task026_input_mass_flow_kg_s": (postpass or {}).get("task026_input_mass_flow_kg_s"),
        "tube_hydraulic_recompute_status": (postpass or {}).get("tube_hydraulic_recompute_status"),
        "shell_hydraulic_recompute_status": (postpass or {}).get(
            "shell_hydraulic_recompute_status"
        ),
        "tube_dp_pa": (postpass or {}).get("recalculated_tube_dp_pa"),
        "shell_dp_pa": (postpass or {}).get("recalculated_shell_dp_pa"),
        "correlation_applicability": (postpass or {}).get("correlation_applicability_status"),
        "live_hydraulic_constraint_status": (postpass or {}).get("hydraulic_constraint_status"),
        "live_hydraulic_postpass_status": (postpass or {}).get("task174_hydraulic_status"),
    }


def run_single_case_n1_with_postpass(
    case: EngineeringCase,
    *,
    budget_s: float,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    selection = enumerate_experimental_rating_candidates(case)
    candidate_id = selection.selected_candidate_ids[0]
    native = build_native_cell_context(case, selection=selection, candidate_id=candidate_id)
    mesh_rows, observations = run_mesh_levels_for_candidate(
        case,
        native,
        mesh_levels=(1,),
        budget_s=budget_s,
        t0=t0,
    )
    n1_row = next(row for row in mesh_rows if int(row.get("mesh_level", -1)) == 1)
    analysis = build_live_multi_mesh_analysis(
        candidate_id=candidate_id,
        rating_request_hash=native.rating_request_hash,
        mesh_level_rows=mesh_rows,
        coarse_obs=observations.get(1),
        fine_obs=None,
    )
    postpass: dict[str, Any] | None = None
    if n1_row.get("mesh_status") == "NUMERIC_VALID" and getattr(
        case, "experimental_live_thermal_hydraulic_postpass", False
    ):
        postpass = attach_live_hydraulic_postpass_for_mesh(
            case,
            native,
            n1_row,
            candidate_id=candidate_id,
        )
        analysis["HIGHEST_MESH_LIVE_HYDRAULIC_POSTPASS"] = postpass
    summary = _mesh_summary(n1_row, postpass)
    if summary["tube_mass_flow_kg_s"] is None:
        summary["tube_mass_flow_kg_s"] = str(tube_stream_spec(case).mass_flow_kg_s)
    return {
        "engineering_case_id": case.engineering_case_id,
        "candidate_id": candidate_id,
        "mesh_level_results": mesh_rows,
        "analysis": analysis,
        "n1_summary": summary,
        "total_wall_seconds": time.perf_counter() - t0,
    }


def run_baseline_vs_variable_comparison(
    baseline_case: EngineeringCase,
    variable_case: EngineeringCase,
    *,
    budget_s: float = 2400.0,
) -> dict[str, Any]:
    baseline = run_single_case_n1_with_postpass(baseline_case, budget_s=budget_s / 2)
    variable = run_single_case_n1_with_postpass(variable_case, budget_s=budget_s / 2)
    base_s = baseline["n1_summary"]
    var_s = variable["n1_summary"]
    base_duty = Decimal(str(base_s["duty_w"]))
    var_duty = Decimal(str(var_s["duty_w"]))
    comparison = {
        "schema_version": "hxforge.variable-tube-mass-flow-comparison.v1",
        "pinned_candidate_id": PINNED_R16_CANDIDATE_ID,
        "baseline": base_s,
        "variable_flow": var_s,
        "duty_delta_w": str(var_duty - base_duty),
        "duty_delta_percent": str((var_duty - base_duty) / base_duty * Decimal("100")),
        "total_wall_seconds": baseline["total_wall_seconds"] + variable["total_wall_seconds"],
    }
    return {
        "comparison": comparison,
        "baseline_run": baseline,
        "variable_run": variable,
    }


def write_r18_engineering_report(payload: dict[str, Any], path: Path) -> None:
    cmp_doc = payload["comparison"]
    base = cmp_doc["baseline"]
    var = cmp_doc["variable_flow"]
    lines = [
        "# R18 Variable Tube Mass Flow Engineering Report",
        "",
        "| Metric | 12 kg/s baseline | Variable tube flow |",
        "| --- | --- | --- |",
        f"| Tube mass flow (kg/s) | {base['tube_mass_flow_kg_s']} | {var['tube_mass_flow_kg_s']} |",
        f"| Shell mass flow (kg/s) | {base['shell_mass_flow_kg_s']} | {var['shell_mass_flow_kg_s']} |",
        f"| Duty (W) | {base['duty_w']} | {var['duty_w']} |",
        f"| Tube outlet (K) | {base['tube_outlet_temperature_k']} | {var['tube_outlet_temperature_k']} |",
        f"| Shell outlet (K) | {base['shell_outlet_temperature_k']} | {var['shell_outlet_temperature_k']} |",
        f"| Tube Reynolds | {base.get('tube_reynolds_number')} | {var.get('tube_reynolds_number')} |",
        f"| Tube Δp (Pa) | {base.get('tube_dp_pa')} | {var.get('tube_dp_pa')} |",
        f"| Shell Δp (Pa) | {base.get('shell_dp_pa')} | {var.get('shell_dp_pa')} |",
        f"| Energy balance residual (W) | {base.get('energy_balance_residual_w')} | {var.get('energy_balance_residual_w')} |",
        f"| Rating status | {base.get('rating_status')} | {var.get('rating_status')} |",
        f"| Correlation applicability | {base.get('correlation_applicability')} | {var.get('correlation_applicability')} |",
        f"| Live hydraulic constraint | {base.get('live_hydraulic_constraint_status')} | {var.get('live_hydraulic_constraint_status')} |",
        "",
        f"Duty delta: {cmp_doc['duty_delta_w']} W ({cmp_doc['duty_delta_percent']} %)",
        f"Total wall time: {cmp_doc['total_wall_seconds']} s",
        "",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_comparison_artifacts(payload: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "R18_VARIABLE_TUBE_FLOW_COMPARISON.json").write_text(
        json.dumps(payload["comparison"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_r18_engineering_report(payload, output_dir / "R18_ENGINEERING_REPORT.md")
