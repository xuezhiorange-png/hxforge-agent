#!/usr/bin/env python3
"""TASK_ID=V08_03_SHELL_052_THERMAL_AUTHORITY_AND_MARGIN_VALIDATION delivery runner."""
# ruff: noqa: E402

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
from prototypes.v08_general_user_case.loader import load_general_user_design_case_json
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import load_case_bindings
from prototypes.v08_thermal_rating.bvp_gate_evidence_v08 import BVP_PROTOTYPE_ROUTE
from prototypes.v08_thermal_rating.case_identity_v08 import CASE_330KW_ID, FIXTURE_330
from prototypes.v08_thermal_rating.recovered_shell_052_full_chain_v08 import (
    FROZEN_SHELL_052_CANDIDATE_ID,
    FROZEN_SHELL_052_GEOMETRY_V2,
)
from prototypes.v08_thermal_rating.shell_052_thermal_authority_and_margin_v08 import (
    run_shell_052_thermal_authority_and_margin,
)
from prototypes.v08_thermal_rating.v08_ci_status import ci_status_for_head

PR_NUMBER = 325


def _git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=_REPO, text=True).strip()


def main() -> None:
    out = Path(
        "/opt/cursor/artifacts/v08_03_shell_052_thermal_authority_and_margin_validation.json"
    )
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    head = _git_head()
    report = run_shell_052_thermal_authority_and_margin(normalized, handoff, provider=provider)

    payload: dict[str, Any] = {
        "TASK_ID": "V08_03_SHELL_052_THERMAL_AUTHORITY_AND_MARGIN_VALIDATION",
        "PR_NUMBER": PR_NUMBER,
        "HEAD_SHA": head,
        "CI_STATUS": ci_status_for_head(head),
        "CASE_ID": CASE_330KW_ID,
        "CANDIDATE_ID": FROZEN_SHELL_052_CANDIDATE_ID,
        "GEOMETRY_V2": FROZEN_SHELL_052_GEOMETRY_V2,
        "TASK037_STATUS": report.task037_status,
        "WALL_MATERIAL_AUTHORITY": report.wall_material_authority,
        "WALL_CONDUCTIVITY_W_M_K": report.wall_conductivity_w_m_k or "unavailable",
        "WALL_RESISTANCE": report.wall_resistance_outer_m2_k_w or "unavailable",
        "UA_W_K": report.ua_w_k or "unavailable",
        "EPSILON_NTU_Q_W": report.epsilon_ntu_q_w or "unavailable",
        "TUBE_OUTLET_K": report.tube_outlet_k or "unavailable",
        "SHELL_OUTLET_K": report.shell_outlet_k or "unavailable",
        "NTU": report.ntu,
        "CR": report.cr,
        "THERMAL_PRESCREEN": report.thermal_prescreen,
        "TUBE_FULL_DP_PA": report.tube_full_dp_pa,
        "SHELL_FULL_DP_PA": report.shell_full_dp_pa,
        "TUBE_DP_MARGIN_PA": report.tube_dp_margin_pa,
        "SHELL_DP_MARGIN_PA": report.shell_dp_margin_pa,
        "HIGH_TUBE_DP_PA": report.high_tube_dp_pa,
        "HIGH_SHELL_DP_PA": report.high_shell_dp_pa,
        "HIGH_FAILURE_COMPONENT": report.high_failure_component,
        "NOZZLE_DESIGN_HASH": report.nozzle_design_hash,
        "NOZZLE_MANUFACTURING_AUTHORITY": report.nozzle_manufacturing_authority,
        "MID_HYDRAULIC_MATHEMATICAL_PASS": report.mid_hydraulic_mathematical_pass,
        "MID_HYDRAULIC_DESIGN_ROBUSTNESS": report.mid_hydraulic_design_robustness,
        "HIGH_HYDRAULIC": report.high_hydraulic,
        "HYDRAULIC_ROBUSTNESS": report.hydraulic_robustness,
        "GEOMETRY_IDENTITY_REPLAY": report.geometry_identity_replay,
        "DESIGN_DECISION": report.design_decision,
        "NEXT_REQUIRED_ENGINEERING_ACTION": report.next_required_engineering_action,
        "PRODUCTION_TASK172": "BLOCKED",
        "PRODUCTION_TASK173": "BLOCKED",
        "ENGINEERING_ACCEPTANCE": "BLOCKED",
        "DISTINCT_FULLY_CONVERGED": 0,
        "BVP_ROUTE": BVP_PROTOTYPE_ROUTE,
        "PRODUCTION_CONTRACT_CHANGE_AUTHORIZED": False,
        "PRODUCTION_SOLVER_REPLACED": False,
        "MERGE_AUTHORIZED": False,
        "TASK037_RESULT_HASH": report.task037_result_hash,
        "SENSITIVITY_NOTES": list(report.sensitivity_notes),
        "report": asdict(report),
    }
    case_raw = json.loads(FIXTURE_330.read_text(encoding="utf-8"))
    _ = load_general_user_design_case_json(json.dumps(case_raw))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
