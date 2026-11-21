#!/usr/bin/env python3
"""TASK_ID=V08_03_RECOVERED_SHELL_052_FULL_CHAIN_VALIDATION delivery runner."""
# ruff: noqa: E402

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(_REPO), str(_REPO / "src")]

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import load_case_bindings
from prototypes.v08_thermal_rating.bvp_gate_evidence_v08 import BVP_PROTOTYPE_ROUTE
from prototypes.v08_thermal_rating.case_identity_v08 import CASE_330KW_ID, FIXTURE_330
from prototypes.v08_thermal_rating.recovered_shell_052_full_chain_v08 import (
    run_recovered_shell_052_full_chain,
)

PR_NUMBER = 325


def _git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=_REPO, text=True).strip()


def _ci_status() -> str:
    try:
        out = subprocess.check_output(
            [
                "gh",
                "run",
                "list",
                "--repo",
                "xuezhiorange-png/hxforge-agent",
                "--branch",
                "cursor/v08-03-live-thermal-rating-1201",
                "--limit",
                "3",
                "--json",
                "conclusion,status,number",
            ],
            cwd=_REPO,
            text=True,
        )
        rows = json.loads(out)
        for row in rows:
            if row.get("number") in (1599, 1600):
                num = row.get("number")
                if row.get("status") != "completed":
                    return f"in_progress_{num}"
                return f"{row.get('conclusion')}_{num}"
        if rows and rows[0].get("status") != "completed":
            return f"in_progress_{rows[0].get('number', '?')}"
        return str(rows[0].get("conclusion") if rows else "unknown")
    except Exception:
        return "unknown"


def main() -> None:
    out = Path("/opt/cursor/artifacts/v08_03_recovered_shell_052_full_chain_validation.json")
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    report = run_recovered_shell_052_full_chain(normalized, handoff, provider=provider)
    thermal = report.thermal

    payload: dict[str, Any] = {
        "TASK_ID": "V08_03_RECOVERED_SHELL_052_FULL_CHAIN_VALIDATION",
        "PR_NUMBER": PR_NUMBER,
        "HEAD_SHA": _git_head(),
        "CI_STATUS": _ci_status(),
        "CASE_ID": CASE_330KW_ID,
        "SHELL_052_TASK168": report.shell_052_task168,
        "SHELL_052_GEOMETRY_V2": report.geometry_identity_v2 or "none",
        "SHELL_052_PHYSICAL_TUBE_COUNT": report.physical_tube_count,
        "SHELL_052_BAFFLE_COUNT": report.baffle_count,
        "SHELL_052_BAFFLE_CUT": report.baffle_cut_fraction,
        "SHELL_052_PLACEMENT_ENVELOPE_M": report.placement_envelope_m,
        "SHELL_052_CANDIDATE_ID": report.candidate_id,
        "SHELL_052_TASK168_REQUEST_DIGEST": report.task168_request_digest,
        "SHELL_052_LAYOUT_HASH": report.layout_hash,
        "SHELL_052_TASK024_GEOMETRY_HASH": report.task024_geometry_hash,
        "SHELL_052_TASK166": report.task166_status,
        "SHELL_052_TASK166_APPLICABILITY": report.task166_applicability,
        "SHELL_052_TASK174": report.task174_status,
        "SHELL_052_BELL_DP_PA": report.bell_dp_pa,
        "SHELL_052_TUBE_FULL_DP_PA": report.tube_full_dp_pa or "not_run",
        "SHELL_052_SHELL_FULL_DP_PA": report.shell_full_dp_pa or "not_run",
        "SHELL_052_MID_HYDRAULIC": report.mid_hydraulic,
        "SHELL_052_HIGH_HYDRAULIC": report.high_hydraulic,
        "NOZZLE_VELOCITY_CHECK": report.nozzle_velocity_check,
        "PROVEN_INFEASIBLE_LOWER_BOUND": report.proven_infeasible_lower_bound,
        "LOWER_BOUND_MID_SHELL_MIN_PA": report.lower_bound_mid_shell_min_pa,
        "FIRST_HYDRAULIC_BLOCKER": report.first_hydraulic_blocker,
        "THERMAL_PRESCREEN": thermal.status if thermal else "NOT_EVALUATED",
        "UA_W_K": thermal.ua_w_per_k if thermal else "unavailable",
        "EPSILON_NTU_Q_W": thermal.epsilon_ntu_q_w if thermal else "unavailable",
        "TARGET_DUTY_GAP_W": thermal.target_duty_gap_w if thermal else "unavailable",
        "PREDICTED_TUBE_OUTLET_K": thermal.predicted_tube_outlet_k if thermal else "unavailable",
        "PREDICTED_SHELL_OUTLET_K": thermal.predicted_shell_outlet_k if thermal else "unavailable",
        "WALL_RESISTANCE_SOURCE": thermal.wall_resistance_source if thermal else None,
        "PROPERTY_BASIS": thermal.property_basis if thermal else None,
        "THERMAL_PRESCREEN_NOTES": list(thermal.notes) if thermal else [],
        "GEOMETRY_IDENTITY_V2_BOUND_TO_RESULTS": report.geometry_identity_v2_bound_to_results,
        "DESIGN_DECISION": report.design_decision,
        "NEXT_REQUIRED_ENGINEERING_CHANGE": report.next_required_engineering_change,
        "PRODUCTION_TASK172": "BLOCKED",
        "PRODUCTION_TASK173": "BLOCKED",
        "ENGINEERING_ACCEPTANCE": "BLOCKED",
        "BVP_ROUTE": BVP_PROTOTYPE_ROUTE,
        "PRODUCTION_CONTRACT_CHANGE_AUTHORIZED": False,
        "PRODUCTION_SOLVER_REPLACED": False,
        "MERGE_AUTHORIZED": False,
    }
    if report.hydraulic_report:
        mid = next(
            s for s in report.hydraulic_report.scenarios if s.scenario_key == "mid_band"
        )
        payload["MID_SHELL_BREAKDOWN"] = dict(mid.shell_breakdown)
        payload["MID_TUBE_BREAKDOWN"] = dict(mid.tube_breakdown)
        payload["TASK174_PARTIAL"] = {
            "tube_dp_pa": report.hydraulic_report.task174_partial.tube_dp_pa,
            "shell_bell_dp_pa": report.hydraulic_report.task174_partial.shell_bell_total_dp_pa,
        }
    recovered = report.recovered
    if recovered is not None:
        t166 = recovered.structural_bundle.bundle.task166_result
        from hexagent.exchangers.shell_tube.bell_delaware.models import Task166Result

        if isinstance(t166, Task166Result):
            payload["TASK166_BELL_DP_BREAKDOWN"] = {
                "ideal_crossflow_dp_pa": str(t166.ideal_crossflow_pressure_drop),
                "crossflow_dp_pa": str(t166.crossflow_pressure_drop),
                "window_dp_pa": str(t166.window_pressure_drop),
                "end_zone_dp_pa": str(t166.end_zone_pressure_drop),
                "total_shell_pressure_drop_pa": str(t166.total_shell_pressure_drop),
            }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()