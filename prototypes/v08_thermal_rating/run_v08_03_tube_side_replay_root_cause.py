#!/usr/bin/env python3
"""TASK_ID=V08_03_TUBE_SIDE_REPLAY_ROOT_CAUSE_AND_DESIGN_DECISION delivery runner."""
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
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_330
from prototypes.v08_thermal_rating.tube_side_replay_root_cause_v08 import (
    combo_root_cause_delivery_key,
    run_tube_side_replay_root_cause_analysis,
    write_root_cause_artifact,
)
from prototypes.v08_thermal_rating.v08_ci_status import ci_status_for_head

PR_NUMBER = 325
ARTIFACT = Path("docs/tasks/evidence/V08-03-tube-side-replay-root-cause-r1.json")


def _combo(report: Any, key: str) -> Any:
    for c in report.combos:
        if c.combo_key == key:
            return c
    raise KeyError(key)


def main() -> None:
    artifacts = Path("/opt/cursor/artifacts")
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=_REPO, text=True).strip()
    report = run_tube_side_replay_root_cause_analysis(normalized, handoff, provider=provider)
    write_root_cause_artifact(report, _REPO / ARTIFACT)
    write_root_cause_artifact(report, artifacts / ARTIFACT.name)

    c55085 = _combo(report, "L5.5_scale0.85")
    c55090 = _combo(report, "L5.5_scale0.90")
    c60085 = _combo(report, "L6.0_scale0.85")
    c60090 = _combo(report, "L6.0_scale0.90")

    payload: dict[str, Any] = {
        "TASK_ID": "V08_03_TUBE_SIDE_REPLAY_ROOT_CAUSE_AND_DESIGN_DECISION",
        "PR_NUMBER": PR_NUMBER,
        "HEAD_SHA": head,
        "CI_STATUS": ci_status_for_head(head),
        "FROZEN_CANDIDATE_C_UNCHANGED": report.frozen_candidate_c_unchanged,
        "COMBO_55_085_ROOT_CAUSE": combo_root_cause_delivery_key(c55085),
        "COMBO_55_090_ROOT_CAUSE": combo_root_cause_delivery_key(c55090),
        "COMBO_60_085_ROOT_CAUSE": combo_root_cause_delivery_key(c60085),
        "COMBO_60_090_ROOT_CAUSE": combo_root_cause_delivery_key(c60090),
        "TASK021_REPLAY_STATUS": report.task021_replay_status,
        "TASK025_BLOCKERS": list(report.task025_blockers),
        "TASK026_BLOCKERS": list(report.task026_blockers),
        "TASK168_STAGE_EVIDENCE": list(report.task168_stage_evidence),
        "INCORRECT_REJECTION_ATTRIBUTION_FIXED": report.incorrect_rejection_attribution_fixed,
        "BINDING_DEFECT_CONFIRMED": report.binding_defect_confirmed,
        "PHYSICAL_APPLICABILITY_BLOCKER_CONFIRMED": report.physical_applicability_blocker_confirmed,
        "RECOVERED_VALID_VARIANT_COUNT": report.recovered_valid_variant_count,
        "HIGH_K_JOINT_PRESCREEN_PASS_COUNT": report.high_k_joint_prescreen_pass_count,
        "NEW_TUBE_GEOMETRY_AUTHORITY_REQUIRED": report.new_tube_geometry_authority_required,
        "NEXT_REQUIRED_ENGINEERING_CHANGE": report.next_required_engineering_change,
        "PRODUCTION_TASK172": "BLOCKED",
        "PRODUCTION_TASK173": "BLOCKED",
        "ENGINEERING_ACCEPTANCE": "BLOCKED",
        "BVP_ROUTE": BVP_PROTOTYPE_ROUTE,
        "MERGE_AUTHORIZED": False,
        "artifact_path": str(ARTIFACT),
    }
    out = artifacts / "v08_03_tube_side_replay_root_cause.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
