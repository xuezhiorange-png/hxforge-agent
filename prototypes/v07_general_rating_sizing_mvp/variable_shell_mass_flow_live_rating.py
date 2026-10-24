"""R19: new shell mass flow n=1 rating vs pinned 12/20 baseline reference."""

# ruff: noqa: E501

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from prototypes.v07_general_rating_sizing_mvp.case_streams import (
    shell_stream_spec,
    tube_stream_spec,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.variable_tube_mass_flow_live_rating import (
    run_single_case_n1_with_postpass,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BASELINE_REFERENCE = REPO_ROOT / "tests/fixtures/r19_baseline_12_20_reference.json"


def _summary_from_postpass(row: dict[str, Any], postpass: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "tube_mass_flow_kg_s": (postpass or {}).get("tube_mass_flow_kg_s"),
        "shell_mass_flow_kg_s": (postpass or {}).get("shell_mass_flow_kg_s"),
        "duty_w": row.get("total_duty_w"),
        "tube_outlet_temperature_k": row.get("tube_outlet_temperature_k"),
        "shell_outlet_temperature_k": row.get("shell_outlet_temperature_k"),
        "energy_balance_residual_w": row.get("energy_balance_residual_w"),
        "rating_status": row.get("mesh_status") or row.get("status"),
        "failure_code": row.get("failure_code"),
        "task172_local_evaluation_count": row.get("task172_local_evaluation_count"),
        "wall_seconds": row.get("wall_seconds"),
        "tube_reynolds_number": (postpass or {}).get("tube_reynolds_number"),
        "shell_reynolds_number": (postpass or {}).get("shell_reynolds_number"),
        "task032_input_mass_flow_kg_s": (postpass or {}).get("task032_input_mass_flow_kg_s"),
        "tube_hydraulic_recompute_status": (postpass or {}).get("tube_hydraulic_recompute_status"),
        "shell_side_heat_transfer_coefficient_w_m2_k": (postpass or {}).get(
            "shell_side_heat_transfer_coefficient_w_m2_k"
        ),
        "tube_dp_pa": (postpass or {}).get("recalculated_tube_dp_pa"),
        "shell_dp_pa": (postpass or {}).get("recalculated_shell_dp_pa"),
        "shell_outlet_pressure_pa": (postpass or {}).get("shell_outlet_pressure_pa"),
        "correlation_applicability": (postpass or {}).get("correlation_applicability_status"),
        "live_hydraulic_constraint_status": (postpass or {}).get("hydraulic_constraint_status"),
    }


def load_baseline_reference(path: Path | None = None) -> dict[str, Any]:
    ref_path = path or DEFAULT_BASELINE_REFERENCE
    return json.loads(ref_path.read_text(encoding="utf-8"))


def run_new_shell_flow_n1_rating(
    case: EngineeringCase,
    *,
    budget_s: float,
) -> dict[str, Any]:
    run = run_single_case_n1_with_postpass(case, budget_s=budget_s)
    n1_row = next(row for row in run["mesh_level_results"] if int(row.get("mesh_level", -1)) == 1)
    postpass = run["analysis"].get("HIGHEST_MESH_LIVE_HYDRAULIC_POSTPASS")
    summary = _summary_from_postpass(n1_row, postpass)
    if summary["tube_mass_flow_kg_s"] is None:
        summary["tube_mass_flow_kg_s"] = str(tube_stream_spec(case).mass_flow_kg_s)
    if summary["shell_mass_flow_kg_s"] is None:
        summary["shell_mass_flow_kg_s"] = str(shell_stream_spec(case).mass_flow_kg_s)
    return {
        "run": run,
        "n1_summary": summary,
        "total_wall_seconds": run["total_wall_seconds"],
    }


def build_comparison_against_baseline(
    baseline: dict[str, Any],
    new_flow: dict[str, Any],
) -> dict[str, Any]:
    base_duty = Decimal(str(baseline["duty_w"]))
    new_status = new_flow.get("rating_status")
    comparison: dict[str, Any] = {
        "schema_version": "hxforge.variable-shell-mass-flow-comparison.v1",
        "baseline_source": baseline.get("source"),
        "baseline": baseline,
        "variable_flow": new_flow,
    }
    if new_status != "NUMERIC_VALID" or new_flow.get("duty_w") is None:
        comparison["rating_outcome"] = "BLOCKED"
        comparison["failure_code"] = new_flow.get("failure_code")
        return comparison
    new_duty = Decimal(str(new_flow["duty_w"]))
    comparison["rating_outcome"] = "NUMERIC_VALID"
    comparison["duty_delta_w"] = str(new_duty - base_duty)
    comparison["duty_delta_percent"] = str((new_duty - base_duty) / base_duty * Decimal("100"))
    return comparison


def write_r19_report(comparison: dict[str, Any], path: Path) -> None:
    base = comparison["baseline"]
    var = comparison["variable_flow"]
    lines = [
        "# R19 Variable Shell Mass Flow Engineering Report",
        "",
        f"Baseline source: {comparison.get('baseline_source')}",
        "",
        "| Metric | 12/20 kg/s (reference) | New shell flow |",
        "| --- | --- | --- |",
        f"| Tube mass flow (kg/s) | {base['tube_mass_flow_kg_s']} | {var.get('tube_mass_flow_kg_s')} |",
        f"| Shell mass flow (kg/s) | {base['shell_mass_flow_kg_s']} | {var.get('shell_mass_flow_kg_s')} |",
        f"| Duty (W) | {base.get('duty_w')} | {var.get('duty_w')} |",
        f"| Tube outlet (K) | {base.get('tube_outlet_temperature_k')} | {var.get('tube_outlet_temperature_k')} |",
        f"| Shell outlet (K) | {base.get('shell_outlet_temperature_k')} | {var.get('shell_outlet_temperature_k')} |",
        f"| Shell Reynolds | {base.get('shell_reynolds_number')} | {var.get('shell_reynolds_number')} |",
        f"| Shell HTC (W/m²K) | {base.get('shell_side_heat_transfer_coefficient_w_m2_k')} | {var.get('shell_side_heat_transfer_coefficient_w_m2_k')} |",
        f"| Shell Δp (Pa) | {base.get('shell_dp_pa')} | {var.get('shell_dp_pa')} |",
        f"| Energy balance residual (W) | {base.get('energy_balance_residual_w')} | {var.get('energy_balance_residual_w')} |",
        f"| Rating status | {base.get('rating_status')} | {var.get('rating_status')} |",
        f"| Correlation applicability | {base.get('correlation_applicability')} | {var.get('correlation_applicability')} |",
        f"| Live hydraulic constraint | {base.get('live_hydraulic_constraint_status')} | {var.get('live_hydraulic_constraint_status')} |",
        "",
    ]
    if comparison.get("duty_delta_w"):
        lines.append(
            f"Duty delta: {comparison['duty_delta_w']} W ({comparison.get('duty_delta_percent')} %)"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
