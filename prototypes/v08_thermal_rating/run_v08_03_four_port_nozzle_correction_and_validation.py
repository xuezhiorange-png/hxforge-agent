#!/usr/bin/env python3
"""TASK_ID=V08_03_FOUR_PORT_NOZZLE_CORRECTION_AND_VALIDATION delivery runner."""
# ruff: noqa: E402, E501

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
from prototypes.v08_thermal_rating.first_joint_candidate_identity_v08 import (
    FROZEN_FIRST_JOINT_CANDIDATE_ID,
    FROZEN_FIRST_JOINT_GEOMETRY_V2,
)
from prototypes.v08_thermal_rating.four_port_nozzle_correction_and_validation_v08 import (
    run_four_port_nozzle_correction_and_validation,
    write_four_port_trial_artifact,
)
from prototypes.v08_thermal_rating.v08_ci_status import ci_status_for_head

PR_NUMBER = 325


def _git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=_REPO, text=True).strip()


def main() -> None:
    artifacts = Path("/opt/cursor/artifacts")
    repo_out = _REPO / "docs/tasks/evidence/V08-03-four-port-nozzle-correction-trials-r1.json"
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    head = _git_head()
    report = run_four_port_nozzle_correction_and_validation(normalized, handoff, provider=provider)
    write_four_port_trial_artifact(report, artifacts / "four_port_nozzle_correction_trials.json")
    write_four_port_trial_artifact(report, repo_out)
    sel = report.selected_trial
    payload: dict[str, Any] = {
        "TASK_ID": "V08_03_FOUR_PORT_NOZZLE_CORRECTION_AND_VALIDATION",
        "PR_NUMBER": PR_NUMBER,
        "HEAD_SHA": head,
        "CI_STATUS": ci_status_for_head(head),
        "CASE_ID": CASE_330KW_ID,
        "CANDIDATE_ID": FROZEN_FIRST_JOINT_CANDIDATE_ID,
        "GEOMETRY_V2": FROZEN_FIRST_JOINT_GEOMETRY_V2,
        "SELECTED_TUBE_ID_MM": report.selected_tube_id_mm,
        "SELECTED_SHELL_ID_MM": report.selected_shell_id_mm,
        "FOUR_PORT_STRICT_VELOCITY_CHECK": report.four_port_strict_velocity_check,
        "TUBE_INLET_V": report.tube_inlet_v,
        "TUBE_OUTLET_V": report.tube_outlet_v,
        "SHELL_INLET_V": report.shell_inlet_v,
        "SHELL_OUTLET_V": report.shell_outlet_v,
        "MID_TUBE_DP_PA": sel.mid_tube_dp_pa if sel else None,
        "MID_SHELL_DP_PA": sel.mid_shell_dp_pa if sel else None,
        "MID_TUBE_MARGIN_PA": sel.mid_tube_margin_pa if sel else None,
        "MID_SHELL_MARGIN_PA": sel.mid_shell_margin_pa if sel else None,
        "HIGH_TUBE_DP_PA": sel.high_tube_dp_pa if sel else None,
        "HIGH_SHELL_DP_PA": sel.high_shell_dp_pa if sel else None,
        "CLEAN_Q_W": report.clean_q_w,
        "MID_JOINT_PRESCREEN": sel.mid_joint_prescreen if sel else "BLOCKED",
        "HIGH_JOINT_PRESCREEN": sel.high_joint_prescreen if sel else "BLOCKED",
        "OUTLET_PROPERTY_CONSISTENCY": report.outlet_property_consistency,
        "FIXED_NOZZLE_OVERRIDE_CHECK": report.fixed_nozzle_override_check,
        "NOZZLE_MANUFACTURING_AUTHORITY": "PROVISIONAL",
        "PRODUCTION_TASK172": "BLOCKED",
        "PRODUCTION_TASK173": "BLOCKED",
        "ENGINEERING_ACCEPTANCE": "BLOCKED",
        "BVP_ROUTE": BVP_PROTOTYPE_ROUTE,
        "MERGE_AUTHORIZED": False,
        "artifact_path": str(repo_out.relative_to(_REPO)),
    }
    out = artifacts / "v08_03_four_port_nozzle_correction_and_validation.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
