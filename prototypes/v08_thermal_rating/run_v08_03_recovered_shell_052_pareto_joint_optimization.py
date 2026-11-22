#!/usr/bin/env python3
"""TASK_ID=V08_03_RECOVERED_052_PARETO_JOINT_OPTIMIZATION delivery runner."""
# ruff: noqa: E402, E501

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(_REPO), str(_REPO / "src")]

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import load_case_bindings
from prototypes.v08_thermal_rating.bvp_gate_evidence_v08 import BVP_PROTOTYPE_ROUTE
from prototypes.v08_thermal_rating.case_identity_v08 import CASE_330KW_ID, FIXTURE_330
from prototypes.v08_thermal_rating.recovered_shell_052_pareto_joint_v08 import (
    run_recovered_shell_052_pareto_joint_optimization,
)
from prototypes.v08_thermal_rating.v08_ci_status import ci_status_for_head

PR_NUMBER = 325


def _git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=_REPO, text=True).strip()


def _json_ready(value: Any) -> Any:
    from decimal import Decimal

    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "__dataclass_fields__"):
        return {k: _json_ready(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {k: _json_ready(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(v) for v in value]
    return value


def main() -> None:
    out = Path("/opt/cursor/artifacts/v08_03_recovered_shell_052_pareto_joint_optimization.json")
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    head = _git_head()
    report = run_recovered_shell_052_pareto_joint_optimization(
        normalized, handoff, provider=provider
    )
    best = report.best
    nv = "BLOCKED"
    if best and best.hydraulic:
        nv = best.hydraulic.nozzle_velocity_check

    payload: dict[str, Any] = {
        "TASK_ID": "V08_03_RECOVERED_052_PARETO_JOINT_OPTIMIZATION",
        "PR_NUMBER": PR_NUMBER,
        "HEAD_SHA": head,
        "CI_STATUS": ci_status_for_head(head),
        "CASE_ID": CASE_330KW_ID,
        "RECOVERED_052_INCLUDED": report.recovered_shell_052_included,
        "PREVIOUS_EXPERIMENTAL_COUNT": report.previous_experimental_count,
        "NEWLY_GENERATED_COUNT": report.newly_generated_count,
        "DISTINCT_V2_GEOMETRIES": report.distinct_v2_geometries,
        "TASK168_VALID_COUNT": report.task168_valid_count,
        "CLEAN_BASELINE_Q_W": report.clean_baseline_q_w,
        "CLEAN_BASELINE_UA_W_K": report.clean_baseline_ua_w_k,
        "REQUIRED_UA_W_K": report.required_ua_w_k,
        "CLEAN_UA_DEFICIT_W_K": report.clean_ua_deficit_w_k,
        "MID_JOINT_PRESCREEN_PASS_COUNT": report.mid_joint_prescreen_pass_count,
        "ALL_SCENARIO_PRESCREEN_PASS_COUNT": report.all_scenario_prescreen_pass_count,
        "BEST_CANDIDATE_ID": best.candidate_id if best else "none",
        "BEST_GEOMETRY_V2": best.geometry_v2 if best else "none",
        "BEST_TUBE_COUNT": best.physical_tube_count if best else "unavailable",
        "BEST_TUBE_LENGTH_M": best.tube_length_m if best else "unavailable",
        "BEST_SHELL_DIAMETER_M": best.shell_diameter_m if best else "unavailable",
        "BEST_CLEAN_Q_W": best.clean_thermal.epsilon_ntu_q_w if best else "unavailable",
        "BEST_FOULED_Q_W": best.fouled_thermal.epsilon_ntu_q_w if best else "unavailable",
        "BEST_UA_W_K": best.clean_thermal.ua_w_per_k if best else "unavailable",
        "BEST_MID_TUBE_DP_PA": best.mid_tube_dp_pa if best else "unavailable",
        "BEST_MID_SHELL_DP_PA": best.mid_shell_dp_pa if best else "unavailable",
        "BEST_TUBE_MARGIN_PA": best.tube_margin_pa if best else "unavailable",
        "BEST_SHELL_MARGIN_PA": best.shell_margin_pa if best else "unavailable",
        "BEST_HIGH_TUBE_DP_PA": best.high_tube_dp_pa if best else "unavailable",
        "BEST_HIGH_SHELL_DP_PA": best.high_shell_dp_pa if best else "unavailable",
        "NOZZLE_VELOCITY_CHECK": nv,
        "NOZZLE_MANUFACTURING_AUTHORITY": "PROVISIONAL",
        "DESIGN_DECISION": report.design_decision,
        "NEXT_REQUIRED_ENGINEERING_CHANGE": report.next_required_engineering_change,
        "PRODUCTION_TASK172": "BLOCKED",
        "PRODUCTION_TASK173": "BLOCKED",
        "ENGINEERING_ACCEPTANCE": "BLOCKED",
        "DISTINCT_FULLY_CONVERGED": 0,
        "BVP_ROUTE": BVP_PROTOTYPE_ROUTE,
        "PRODUCTION_CONTRACT_CHANGE_AUTHORIZED": False,
        "PRODUCTION_SOLVER_REPLACED": False,
        "MERGE_AUTHORIZED": False,
        "local_combo_blockers": list(report.local_combo_blockers),
        "pareto_front_ids": [r.candidate_id for r in report.pareto_front],
        "report": _json_ready(report),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
