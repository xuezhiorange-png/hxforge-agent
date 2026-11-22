#!/usr/bin/env python3
"""TASK_ID=V08_03_THERMAL_HYDRAULIC_COOPTIMIZATION_RECOVERY delivery runner."""
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
from prototypes.v08_thermal_rating.v08_ci_status import ci_status_for_head
from prototypes.v08_thermal_rating.v08_thermal_hydraulic_cooptimization_recovery_v08 import (
    run_thermal_hydraulic_cooptimization_recovery,
)

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
    out = Path("/opt/cursor/artifacts/v08_03_thermal_hydraulic_cooptimization_recovery.json")
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    head = _git_head()
    report = run_thermal_hydraulic_cooptimization_recovery(
        normalized, handoff, provider=provider, max_valid=40
    )
    best = report.joint.best
    prov = report.provenance
    payload: dict[str, Any] = {
        "TASK_ID": "V08_03_THERMAL_HYDRAULIC_COOPTIMIZATION_RECOVERY",
        "PR_NUMBER": PR_NUMBER,
        "HEAD_SHA": head,
        "CI_STATUS": ci_status_for_head(head),
        "CASE_ID": CASE_330KW_ID,
        "TASK037_AUTHORITY_PROVENANCE": prov.task037_authority_provenance,
        "MATERIAL_HASH_REUSE_CORRECTED": prov.material_hash_reuse_corrected,
        "FOULING_BASIS_RECONCILED": prov.fouling_basis_reconciled,
        "CLEAN_UA_W_K": report.clean.ua_w_k or "unavailable",
        "CLEAN_EPSILON_NTU_Q_W": report.clean.epsilon_ntu_q_w or "unavailable",
        "FOULED_UA_W_K": report.fouled.ua_w_k or "unavailable",
        "FOULED_EPSILON_NTU_Q_W": report.fouled.epsilon_ntu_q_w or "unavailable",
        "REQUIRED_UA_W_K": report.required_ua_w_k or "unavailable",
        "BASELINE_UA_GAP_W_K": report.baseline_ua_gap_w_k or "unavailable",
        "UA_REQUIRED_INCREASE_FRACTION": report.ua_required_increase_fraction or "unavailable",
        "HIGH_TUBE_DP_EXCESS_PA": report.high_tube_excess_pa or "unavailable",
        "HIGH_SHELL_DP_EXCESS_PA": report.high_shell_excess_pa or "unavailable",
        "NEW_STRUCTURAL_CANDIDATES": report.joint.task168_valid_count,
        "DISTINCT_V2_GEOMETRIES": report.joint.distinct_v2_geometries,
        "TASK168_VALID_COUNT": report.joint.task168_valid_count,
        "MID_THERMAL_HYDRAULIC_PRESCREEN_PASS_COUNT": report.joint.mid_thermal_hydraulic_prescreen_pass_count,
        "ALL_SCENARIO_PRESCREEN_PASS_COUNT": report.joint.all_scenario_prescreen_pass_count,
        "THERMAL_PASS_HYDRAULIC_FAIL_COUNT": report.joint.thermal_pass_hydraulic_fail_count,
        "HYDRAULIC_PASS_THERMAL_FAIL_COUNT": report.joint.hydraulic_pass_thermal_fail_count,
        "BEST_NEW_CANDIDATE_ID": best.candidate_id if best else "none",
        "BEST_NEW_GEOMETRY_V2": best.geometry_v2 if best else "none",
        "BEST_NEW_CLASSIFICATION": best.classification if best else "none",
        "BEST_NEW_Q_W": best.clean_thermal.epsilon_ntu_q_w if best else "unavailable",
        "BEST_NEW_UA_W_K": best.clean_thermal.ua_w_per_k if best else "unavailable",
        "BEST_NEW_TUBE_DP_PA": best.mid_tube_dp_pa if best else "unavailable",
        "BEST_NEW_SHELL_DP_PA": best.mid_shell_dp_pa if best else "unavailable",
        "BEST_NEW_TUBE_MARGIN_PA": best.mid_tube_margin_pa if best else "unavailable",
        "BEST_NEW_SHELL_MARGIN_PA": best.mid_shell_margin_pa if best else "unavailable",
        "NEXT_REQUIRED_ENGINEERING_ACTION": (
            "No experimental joint mid-pass in discrete space; best 0.45 m achieves CLEAN ε-NTU duty "
            "but shell full-path dp blocked — enlarge shell / reduce loss or relax envelope within "
            "approved discrete authority."
            if report.joint.mid_thermal_hydraulic_prescreen_pass_count == 0
            else "Review mid joint-pass candidates for experimental follow-up."
        ),
        "PRODUCTION_TASK172": "BLOCKED",
        "PRODUCTION_TASK173": "BLOCKED",
        "ENGINEERING_ACCEPTANCE": "BLOCKED",
        "BVP_ROUTE": BVP_PROTOTYPE_ROUTE,
        "PRODUCTION_CONTRACT_CHANGE_AUTHORIZED": False,
        "PRODUCTION_SOLVER_REPLACED": False,
        "MERGE_AUTHORIZED": False,
        "provenance_audit": _json_ready(prov),
        "baseline_clean": _json_ready(report.clean),
        "baseline_fouled": _json_ready(report.fouled),
        "joint_summary": _json_ready(report.joint),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
