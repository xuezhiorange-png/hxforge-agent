#!/usr/bin/env python3
"""TASK_ID=V08_03_FIRST_JOINT_CANDIDATE_FREEZE_AND_RISK_VALIDATION delivery runner."""
# ruff: noqa: E402, E501

from __future__ import annotations

import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(_REPO), str(_REPO / "src")]

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import load_case_bindings
from prototypes.v08_thermal_rating.bvp_gate_evidence_v08 import BVP_PROTOTYPE_ROUTE
from prototypes.v08_thermal_rating.case_identity_v08 import CASE_330KW_ID, FIXTURE_330
from prototypes.v08_thermal_rating.first_joint_candidate_freeze_v08 import (
    ENGINEERING_DESIGN_STATUS,
    run_first_joint_candidate_freeze,
    write_freeze_artifacts,
)
from prototypes.v08_thermal_rating.first_joint_candidate_identity_v08 import (
    FROZEN_FIRST_JOINT_GEOMETRY_V2,
)
from prototypes.v08_thermal_rating.recovered_shell_052_pareto_joint_v08 import (
    run_recovered_shell_052_pareto_joint_optimization,
    select_first_joint_frozen_row,
)
from prototypes.v08_thermal_rating.v08_ci_status import ci_status_for_head

PR_NUMBER = 325


def _git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=_REPO, text=True).strip()


def _nozzle_summary(report_ports: tuple[Any, ...]) -> tuple[str, str]:
    mm: list[str] = []
    vel: list[str] = []
    for p in report_ports:
        d_mm = (Decimal(str(p.inside_diameter_m)) * Decimal("1000")).quantize(Decimal("0.01"))
        mm.append(f"{p.port_id}:{d_mm}")
        vel.append(f"{p.port_id}:{Decimal(str(p.velocity_m_s)).quantize(Decimal('0.001'))}")
    return "/".join(mm), "/".join(vel)


def main() -> None:
    artifacts = Path("/opt/cursor/artifacts")
    repo_spec = _REPO / "docs/tasks/evidence/V08-03-first-joint-candidate-design-spec.json"
    repo_review = _REPO / "docs/tasks/evidence/V08-03-first-joint-candidate-engineering-review.md"
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    head = _git_head()
    pareto = run_recovered_shell_052_pareto_joint_optimization(
        normalized, handoff, provider=provider
    )
    frozen_row = select_first_joint_frozen_row(pareto)
    freeze = run_first_joint_candidate_freeze(normalized, handoff, provider=provider)

    write_freeze_artifacts(
        freeze,
        json_path=artifacts / "first_joint_candidate_design_spec.json",
        md_path=artifacts / "first_joint_candidate_engineering_review.md",
    )
    write_freeze_artifacts(freeze, json_path=repo_spec, md_path=repo_review)

    mid = next(s for s in freeze.hydraulic.scenarios if s.scenario_key == "mid_band")
    high = next(s for s in freeze.hydraulic.scenarios if s.scenario_key == "high_loss_sensitivity")
    target_q = Decimal(str(normalized.target_duty_w))
    q_clean = Decimal(freeze.clean_thermal.epsilon_ntu_q_w or "0")
    q_margin = (q_clean - target_q).quantize(Decimal("0.1"))
    nozzle_mm, nozzle_vel = _nozzle_summary(freeze.hydraulic.ports)

    payload: dict[str, Any] = {
        "TASK_ID": "V08_03_FIRST_JOINT_CANDIDATE_FREEZE_AND_RISK_VALIDATION",
        "PR_NUMBER": PR_NUMBER,
        "HEAD_SHA": head,
        "CI_STATUS": ci_status_for_head(head),
        "CASE_ID": CASE_330KW_ID,
        "FROZEN_CANDIDATE_ID": freeze.candidate_id,
        "FROZEN_GEOMETRY_V2": FROZEN_FIRST_JOINT_GEOMETRY_V2,
        "STRUCTURE_SPEC_COMPLETE": freeze.structure_spec_complete,
        "TUBE_COUNT": freeze.design_spec["geometry"]["physical_tube_count"],
        "TUBE_LENGTH_M": freeze.design_spec["geometry"]["tube_length_m"],
        "SHELL_ID_M": freeze.design_spec["geometry"]["shell_inside_diameter_m"],
        "BAFFLE_COUNT": freeze.design_spec["geometry"]["baffle_count"],
        "BAFFLE_CUT": freeze.design_spec["geometry"]["baffle_cut_fraction"],
        "BAFFLE_SPACING_M": freeze.design_spec["geometry"]["baffle_spacing_m"],
        "CLEAN_Q_W": freeze.clean_thermal.epsilon_ntu_q_w,
        "CLEAN_Q_MARGIN_W": str(q_margin),
        "FOULED_Q_W": freeze.fouled_thermal.epsilon_ntu_q_w,
        "UA_W_K": freeze.clean_thermal.ua_w_per_k,
        "MID_TUBE_DP_PA": mid.tube_full_path_dp_pa,
        "MID_SHELL_DP_PA": mid.shell_full_path_dp_pa,
        "HIGH_TUBE_DP_PA": high.tube_full_path_dp_pa,
        "HIGH_SHELL_DP_PA": high.shell_full_path_dp_pa,
        "NOZZLE_DIAMETERS_MM": nozzle_mm,
        "NOZZLE_VELOCITIES_M_S": nozzle_vel,
        "GENERIC_USER_CONSTRAINTS": freeze.generic_user_constraints,
        "PARETO_MISSING_RESULT_HANDLING": freeze.pareto_missing_result_handling,
        "GEOMETRY_IDENTITY_REPLAY": freeze.geometry_identity_replay,
        "ENGINEERING_DESIGN_STATUS": ENGINEERING_DESIGN_STATUS,
        "FULLY_VALIDATED_CANDIDATE_COUNT": 0,
        "PRODUCTION_TASK172": "BLOCKED",
        "PRODUCTION_TASK173": "BLOCKED",
        "ENGINEERING_ACCEPTANCE": "BLOCKED",
        "BVP_ROUTE": BVP_PROTOTYPE_ROUTE,
        "PRODUCTION_CONTRACT_CHANGE_AUTHORIZED": False,
        "PRODUCTION_SOLVER_REPLACED": False,
        "MERGE_AUTHORIZED": False,
        "PARETO_FROZEN_ROW_CANDIDATE_ID": frozen_row.candidate_id if frozen_row else "none",
        "BVP_GEOMETRY_SEARCH": "STOP",
    }
    out = artifacts / "v08_03_first_joint_candidate_freeze_and_risk_validation.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()