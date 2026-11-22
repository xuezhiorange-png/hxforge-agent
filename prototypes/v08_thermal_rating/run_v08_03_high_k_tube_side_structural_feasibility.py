#!/usr/bin/env python3
"""TASK_ID=V08_03_HIGH_K_TUBE_SIDE_STRUCTURAL_FEASIBILITY delivery runner."""
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
from prototypes.v08_thermal_rating.high_k_tube_side_structural_feasibility_v08 import (
    run_high_k_tube_side_structural_feasibility,
    write_feasibility_artifacts,
)
from prototypes.v08_thermal_rating.v08_ci_status import ci_status_for_head

PR_NUMBER = 325
JSON_REPO = Path("docs/tasks/evidence/V08-03-high-k-tube-side-structural-feasibility-r1.json")
MD_REPO = Path("docs/tasks/evidence/V08-03-high-k-tube-side-structural-feasibility-r1.md")


def _git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=_REPO, text=True).strip()


def main() -> None:
    artifacts = Path("/opt/cursor/artifacts")
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    head = _git_head()
    report = run_high_k_tube_side_structural_feasibility(normalized, handoff, provider=provider)
    write_feasibility_artifacts(
        report, json_path=_REPO / JSON_REPO, md_path=_REPO / MD_REPO
    )
    write_feasibility_artifacts(
        report,
        json_path=artifacts / JSON_REPO.name,
        md_path=artifacts / MD_REPO.name,
    )
    payload: dict[str, Any] = {
        "TASK_ID": "V08_03_HIGH_K_TUBE_SIDE_STRUCTURAL_FEASIBILITY",
        "PR_NUMBER": PR_NUMBER,
        "HEAD_SHA": head,
        "CI_STATUS": ci_status_for_head(head),
        "FROZEN_CANDIDATE_C_UNCHANGED": report.frozen_candidate_c_unchanged,
        "HIGH_TUBE_DP_BASELINE_PA": report.high_tube_dp_baseline_pa,
        "HIGH_TUBE_DP_NOZZLE_LOWER_BOUND_PA": report.high_tube_dp_nozzle_lower_bound_pa,
        "HIGH_TUBE_DP_EXCESS_PA": report.high_tube_dp_excess_pa,
        "TUBE_INTERNAL_FRICTION_DP_PA": report.tube_internal_friction_dp_pa,
        "TUBE_LOCAL_DP_PA": report.tube_local_dp_pa,
        "TUBE_NOZZLE_PAIR_DP_PA": report.tube_nozzle_pair_dp_pa,
        "REQUIRED_INTERNAL_DP_REDUCTION_PA": report.required_internal_dp_reduction_pa,
        "EXISTING_AUTHORIZED_VARIANT_FEASIBLE": report.existing_authorized_variant_feasible,
        "AUTHORIZED_VARIANTS_EVALUATED": report.authorized_variants_evaluated,
        "BEST_VALIDATED_VARIANT_ID": report.best_validated_variant_id or "none",
        "BEST_VALIDATED_VARIANT_GEOMETRY_V2": report.best_validated_variant_geometry_v2 or "none",
        "BEST_VALIDATED_VARIANT_CLEAN_Q_W": report.best_validated_variant_clean_q_w or "unavailable",
        "BEST_VALIDATED_VARIANT_HIGH_TUBE_DP_PA": report.best_validated_variant_high_tube_dp_pa
        or "unavailable",
        "BEST_VALIDATED_VARIANT_HIGH_SHELL_DP_PA": report.best_validated_variant_high_shell_dp_pa
        or "unavailable",
        "BEST_VALIDATED_VARIANT_FOUR_PORT_CHECK": report.best_validated_variant_four_port_check
        or "unavailable",
        "NEW_TUBE_GEOMETRY_AUTHORITY_REQUIRED": report.new_tube_geometry_authority_required,
        "PROPOSED_ENGINEERING_CHANGE": report.proposed_engineering_change,
        "ENGINEERING_SOURCE_STATUS": report.engineering_source_status,
        "DESIGN_DECISION": report.design_decision,
        "PRODUCTION_TASK172": "BLOCKED",
        "PRODUCTION_TASK173": "BLOCKED",
        "ENGINEERING_ACCEPTANCE": "BLOCKED",
        "FULLY_VALIDATED_CANDIDATE_COUNT": 0,
        "BVP_ROUTE": BVP_PROTOTYPE_ROUTE,
        "PRODUCTION_CONTRACT_CHANGE_AUTHORIZED": False,
        "PRODUCTION_SOLVER_REPLACED": False,
        "MERGE_AUTHORIZED": False,
        "artifact_json": str(JSON_REPO),
        "artifact_md": str(MD_REPO),
    }
    out = artifacts / "v08_03_high_k_tube_side_structural_feasibility.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()