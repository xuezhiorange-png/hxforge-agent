#!/usr/bin/env python3
"""TASK_ID=V08_03_CANDIDATE_C_ENGINEERING_EVIDENCE_CLOSURE delivery runner."""
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
from prototypes.v08_thermal_rating.candidate_c_engineering_evidence_closure_v08 import (
    run_candidate_c_engineering_evidence_closure,
    write_candidate_c_artifacts,
)
from prototypes.v08_thermal_rating.candidate_c_identity_v08 import (
    CANDIDATE_C_SHELL_NOZZLE_ID_MM,
    CANDIDATE_C_TUBE_NOZZLE_ID_MM,
)
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_330
from prototypes.v08_thermal_rating.first_joint_candidate_freeze_v08 import (
    ENGINEERING_DESIGN_STATUS,
)
from prototypes.v08_thermal_rating.first_joint_candidate_identity_v08 import (
    FROZEN_FIRST_JOINT_CANDIDATE_ID,
    FROZEN_FIRST_JOINT_GEOMETRY_V2,
)
from prototypes.v08_thermal_rating.v08_ci_status import ci_status_for_head

PR_NUMBER = 325
SPEC_REPO = _REPO / "docs/tasks/evidence/V08-03-candidate-C-design-spec-r1.json"
REVIEW_REPO = _REPO / "docs/tasks/evidence/V08-03-candidate-C-engineering-review-r1.md"


def _git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=_REPO, text=True).strip()


def main() -> None:
    artifacts = Path("/opt/cursor/artifacts")
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    head = _git_head()
    report = run_candidate_c_engineering_evidence_closure(normalized, handoff, provider=provider)
    write_candidate_c_artifacts(
        report,
        json_path=SPEC_REPO,
        md_path=REVIEW_REPO,
    )
    write_candidate_c_artifacts(
        report,
        json_path=artifacts / "V08-03-candidate-C-design-spec-r1.json",
        md_path=artifacts / "V08-03-candidate-C-engineering-review-r1.md",
    )
    payload: dict[str, Any] = {
        "TASK_ID": "V08_03_CANDIDATE_C_ENGINEERING_EVIDENCE_CLOSURE",
        "PR_NUMBER": PR_NUMBER,
        "HEAD_SHA": head,
        "CI_STATUS": ci_status_for_head(head),
        "CANDIDATE_ID": FROZEN_FIRST_JOINT_CANDIDATE_ID,
        "GEOMETRY_V2": FROZEN_FIRST_JOINT_GEOMETRY_V2,
        "C_NOZZLE_DESIGN_HASH": report.nozzle_design_hash,
        "STRUCTURE_IDENTITY_REPLAY": report.structure_identity_replay,
        "OUTLET_PROPERTY_CONSISTENCY": report.outlet_property_consistency,
        "FIXED_NOZZLE_OVERRIDE_CHECK": report.fixed_nozzle_override_check,
        "FOUR_PORT_STRICT_VELOCITY_CHECK": report.four_port_strict_velocity_check,
        "CLEAN_Q_W": report.clean_q_w,
        "FOULED_Q_W": report.fouled_q_w,
        "MID_TUBE_DP_PA": report.mid_tube_dp_pa,
        "MID_SHELL_DP_PA": report.mid_shell_dp_pa,
        "MID_TUBE_MARGIN_PA": report.mid_tube_margin_pa,
        "MID_SHELL_MARGIN_PA": report.mid_shell_margin_pa,
        "HIGH_TUBE_DP_PA": report.high_tube_dp_pa,
        "HIGH_SHELL_DP_PA": report.high_shell_dp_pa,
        "NOZZLE_ONLY_HIGH_K_FEASIBILITY": report.nozzle_only_high_k_feasibility,
        "CANDIDATE_C_DESIGN_SPEC": str(SPEC_REPO.relative_to(_REPO)),
        "CANDIDATE_C_ENGINEERING_REVIEW": str(REVIEW_REPO.relative_to(_REPO)),
        "MID_JOINT_PRESCREEN": report.mid_joint_prescreen,
        "ALL_SCENARIO_PRESCREEN": report.all_scenario_prescreen,
        "ENGINEERING_DESIGN_STATUS": ENGINEERING_DESIGN_STATUS,
        "NOZZLE_MANUFACTURING_AUTHORITY": "PROVISIONAL",
        "FULLY_VALIDATED_CANDIDATE_COUNT": 0,
        "PRODUCTION_TASK172": "BLOCKED",
        "PRODUCTION_TASK173": "BLOCKED",
        "ENGINEERING_ACCEPTANCE": "BLOCKED",
        "BVP_ROUTE": BVP_PROTOTYPE_ROUTE,
        "PRODUCTION_CONTRACT_CHANGE_AUTHORIZED": False,
        "PRODUCTION_SOLVER_REPLACED": False,
        "MERGE_AUTHORIZED": False,
        "scheme_c_nozzles_mm": {
            "tube": str(CANDIDATE_C_TUBE_NOZZLE_ID_MM),
            "shell": str(CANDIDATE_C_SHELL_NOZZLE_ID_MM),
        },
        "outlet_property_failures": list(report.outlet_property_failures),
        "fixed_override_failures": list(report.fixed_override_failures),
        "min_high_tube_dp_at_max_nozzle_pa": report.min_high_tube_dp_at_max_nozzle_pa,
    }
    out = artifacts / "v08_03_candidate_c_engineering_evidence_closure.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
