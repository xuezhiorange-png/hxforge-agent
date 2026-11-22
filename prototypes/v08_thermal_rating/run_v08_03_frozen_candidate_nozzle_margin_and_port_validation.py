#!/usr/bin/env python3
"""TASK_ID=V08_03_FROZEN_CANDIDATE_NOZZLE_MARGIN_AND_PORT_STATE_VALIDATION delivery runner."""
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
)
from prototypes.v08_thermal_rating.first_joint_candidate_identity_v08 import (
    FROZEN_FIRST_JOINT_CANDIDATE_ID,
    FROZEN_FIRST_JOINT_GEOMETRY_V2,
)
from prototypes.v08_thermal_rating.frozen_candidate_nozzle_margin_and_port_validation_v08 import (
    run_frozen_nozzle_margin_and_port_validation,
    write_nozzle_comparison_artifact,
)
from prototypes.v08_thermal_rating.v08_ci_status import ci_status_for_head
from prototypes.v08_thermal_rating.v08_prescreen_validators_v08 import (
    validate_generic_user_constraints,
    validate_pareto_missing_result_handling,
)

PR_NUMBER = 325


def _git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=_REPO, text=True).strip()


def _port_mm(ports: tuple[Any, ...], port_id: str) -> str:
    for p in ports:
        if p.port_id == port_id:
            return str((p.inside_diameter_m * Decimal("1000")).quantize(Decimal("0.01")))
    return "unavailable"


def main() -> None:
    artifacts = Path("/opt/cursor/artifacts")
    repo_cmp = _REPO / "docs/tasks/evidence/V08-03-frozen-nozzle-design-comparison-r1.json"
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    head = _git_head()
    report = run_frozen_nozzle_margin_and_port_validation(normalized, handoff, provider=provider)
    write_nozzle_comparison_artifact(report, artifacts / "frozen_nozzle_design_comparison.json")
    write_nozzle_comparison_artifact(report, repo_cmp)

    mid_b = next(s for s in report.design_b.hydraulic.scenarios if s.scenario_key == "mid_band")
    high_b = next(
        s for s in report.design_b.hydraulic.scenarios if s.scenario_key == "high_loss_sensitivity"
    )
    ports = report.design_b.hydraulic.ports

    payload: dict[str, Any] = {
        "TASK_ID": "V08_03_FROZEN_CANDIDATE_NOZZLE_MARGIN_AND_PORT_STATE_VALIDATION",
        "PR_NUMBER": PR_NUMBER,
        "HEAD_SHA": head,
        "CI_STATUS": ci_status_for_head(head),
        "CASE_ID": CASE_330KW_ID,
        "FROZEN_CANDIDATE_ID": FROZEN_FIRST_JOINT_CANDIDATE_ID,
        "FROZEN_GEOMETRY_V2": FROZEN_FIRST_JOINT_GEOMETRY_V2,
        "BASELINE_NOZZLE_DESIGN_HASH": report.baseline_nozzle_design_hash,
        "OPTIMIZED_NOZZLE_DESIGN_HASH": report.optimized_nozzle_design_hash,
        "OPTIMIZED_TUBE_INLET_ID_MM": _port_mm(ports, "TUBE_INLET"),
        "OPTIMIZED_TUBE_OUTLET_ID_MM": _port_mm(ports, "TUBE_OUTLET"),
        "OPTIMIZED_SHELL_INLET_ID_MM": _port_mm(ports, "SHELL_INLET"),
        "OPTIMIZED_SHELL_OUTLET_ID_MM": _port_mm(ports, "SHELL_OUTLET"),
        "FOUR_PORT_DENSITY_AND_VELOCITY_CHECK": report.four_port_density_and_velocity_check,
        "BASELINE_MID_SHELL_DP_PA": "1179.998631023644509985811160",
        "OPTIMIZED_MID_SHELL_DP_PA": mid_b.shell_full_path_dp_pa,
        "OPTIMIZED_HIGH_SHELL_DP_PA": high_b.shell_full_path_dp_pa,
        "OPTIMIZED_MID_TUBE_DP_PA": mid_b.tube_full_path_dp_pa,
        "OPTIMIZED_HIGH_TUBE_DP_PA": high_b.tube_full_path_dp_pa,
        "MID_JOINT_PRESCREEN": report.design_b.mid_joint_prescreen,
        "HIGH_JOINT_PRESCREEN": report.design_b.high_joint_prescreen,
        "CLEAN_Q_W": report.clean_q_w,
        "CLEAN_Q_MARGIN_W": report.clean_q_margin_w,
        "FOULED_Q_W": report.fouled_q_w,
        "REAL_PERTURBATION_SENSITIVITY": report.real_perturbation_sensitivity,
        "GENERIC_USER_CONSTRAINTS": validate_generic_user_constraints(provider=provider),
        "PARETO_MISSING_RESULT_HANDLING": validate_pareto_missing_result_handling(
            provider=provider
        ),
        "STRUCTURE_SPEC_VALIDATION": "NOT_EVALUATED",
        "NOZZLE_MANUFACTURING_AUTHORITY": "PROVISIONAL",
        "ENGINEERING_DESIGN_STATUS": ENGINEERING_DESIGN_STATUS,
        "HIGH_TUBE_INFEASIBLE_NOTE": report.high_tube_infeasible_note,
        "NEXT_REQUIRED_ENGINEERING_CHANGE": report.next_required_engineering_change,
        "PRODUCTION_TASK172": "BLOCKED",
        "PRODUCTION_TASK173": "BLOCKED",
        "ENGINEERING_ACCEPTANCE": "BLOCKED",
        "DISTINCT_FULLY_CONVERGED": 0,
        "BVP_ROUTE": BVP_PROTOTYPE_ROUTE,
        "PRODUCTION_CONTRACT_CHANGE_AUTHORIZED": False,
        "PRODUCTION_SOLVER_REPLACED": False,
        "MERGE_AUTHORIZED": False,
        "comparison_artifact_path": str(repo_cmp.relative_to(_REPO)),
    }
    out = artifacts / "v08_03_frozen_candidate_nozzle_margin_and_port_validation.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
