#!/usr/bin/env python3
"""TASK_ID=V08_03_ENGINEERING_SHORTLIST_ROBUSTNESS_AND_THERMAL_AUTHORITY delivery runner."""
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
from prototypes.v08_thermal_rating.engineering_shortlist_robustness_v08 import (
    run_engineering_shortlist_robustness,
    write_shortlist_artifacts,
)
from prototypes.v08_thermal_rating.v08_ci_status import ci_status_for_head

PR_NUMBER = 325
ARTIFACT_JSON = Path("docs/tasks/evidence/V08-03-engineering-shortlist-robustness-r2.json")
ARTIFACT_MD = Path("docs/tasks/evidence/V08-03-engineering-shortlist-robustness-r2.md")
TASK_ID = "V08_03_SENSITIVITY_BINDING_INTEGRITY_AND_ROBUSTNESS_EVIDENCE_CORRECTION"


def _choice_key(report: Any, attr: str) -> str | None:
    row = getattr(report, attr, None)
    return row.shortlist_key if row is not None else None


def main() -> None:
    artifacts = Path("/opt/cursor/artifacts")
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=_REPO, text=True).strip()
    report = run_engineering_shortlist_robustness(normalized, handoff, provider=provider)
    write_shortlist_artifacts(report, json_path=_REPO / ARTIFACT_JSON, md_path=_REPO / ARTIFACT_MD)
    write_shortlist_artifacts(
        report,
        json_path=artifacts / ARTIFACT_JSON.name,
        md_path=artifacts / ARTIFACT_MD.name,
    )
    ls = report.layout_status_by_key
    payload: dict[str, Any] = {
        "TASK_ID": TASK_ID,
        "PR_NUMBER": PR_NUMBER,
        "HEAD_SHA": head,
        "CI_STATUS": ci_status_for_head(head),
        "SENSITIVITY_BINDING_ROOT_CAUSE": report.sensitivity_binding_root_cause,
        "LAYOUT_IDENTITY_DRIFT": report.layout_identity_drift_confirmed,
        "ACTUAL_TASK027_BLOCKERS": "BL_T027_UNSUPPORTED_REYNOLDS_REGIME on 241-tube layouts at tube_mdot_minus_1pct/minus_3pct",
        "REPLAY_BINDING_DEFECT_CONFIRMED": report.replay_binding_defect_confirmed,
        "NONBASELINE_SCENARIOS_VALID": report.nonbaseline_scenarios_valid,
        "NONBASELINE_SCENARIOS_BLOCKED": report.nonbaseline_scenarios_blocked,
        "NONBASELINE_HIGH_K_DP_COMPUTED": report.nonbaseline_high_k_dp_computed,
        "CANONICAL_SHORTLIST_SIZE": report.canonical_shortlist_size,
        "DISTINCT_AUDITED_LAYOUT_HASH_COUNT": report.distinct_audited_layout_hash_count,
        "ROBUSTNESS_EVIDENCE_VALID": report.robustness_evidence_valid,
        "UNIQUE_PHYSICAL_LAYOUT_COUNT": report.unique_physical_layout_count,
        "IDENTITY_BINDING_STATUS": report.identity_binding_status,
        "THERMAL_PRIORITY_CANDIDATE": _choice_key(report, "thermal_priority"),
        "HYDRAULIC_PRIORITY_CANDIDATE": _choice_key(report, "hydraulic_priority"),
        "REGIME_ROBUSTNESS_PRIORITY_CANDIDATE": _choice_key(report, "regime_robustness_priority"),
        "ENGINEERING_RECOMMENDED_CANDIDATE": _choice_key(report, "engineering_recommended"),
        "RE_SENSITIVITY_RESULT": report.re_sensitivity_result,
        "HIGH_K_MARGIN_ROBUSTNESS": report.high_k_margin_robustness,
        "CLEAN_330KW_STATUS": report.clean_330kw_status,
        "FOULED_330KW_STATUS": report.fouled_330kw_status,
        "FOULING_AUTHORITY_STATUS": report.fouling_authority_status,
        "TASK173_PRODUCTION_RATING_STATUS": report.task173_production_rating_status,
        "PLACEMENT_ENVELOPE_APPROVAL_REQUIRED": report.placement_envelope_approval_required,
        "NEW_TUBE_CATALOG_RECORD_REQUIRED": report.new_tube_catalog_record_required,
        "FINAL_ENGINEERING_DECISION": report.final_engineering_decision,
        "ENGINEERING_ACCEPTANCE_STATUS": report.engineering_acceptance_status,
        "T235_L5P5_STATUS": ls.get("T235_L5.5"),
        "T235_L6P0_STATUS": ls.get("T235_L6.0"),
        "T241_L5P5_STATUS": ls.get("T241_L5.5"),
        "T241_L6P0_STATUS": ls.get("T241_L6.0"),
        "PR_STATE": "DRAFT",
        "MERGE_AUTHORIZED": False,
        "BVP_ROUTE": BVP_PROTOTYPE_ROUTE,
        "artifact_path": str(ARTIFACT_JSON),
        "supersession_path": "docs/tasks/evidence/V08-03-engineering-shortlist-robustness-supersession-r2.json",
    }
    out = artifacts / "v08_03_engineering_shortlist_robustness_delivery.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()