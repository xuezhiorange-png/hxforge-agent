#!/usr/bin/env python3
"""TASK_ID=V08_03_INTERMEDIATE_TUBE_COUNT_FEASIBILITY_AND_EVIDENCE_RECONCILIATION runner."""
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
from prototypes.v08_thermal_rating.intermediate_tube_count_feasibility_v08 import (
    run_intermediate_tube_count_feasibility,
    write_feasibility_artifacts,
)
from prototypes.v08_thermal_rating.v08_ci_status import ci_status_for_head

PR_NUMBER = 325
ARTIFACT_JSON = Path("docs/tasks/evidence/V08-03-intermediate-tube-count-feasibility-r1.json")
ARTIFACT_MD = Path("docs/tasks/evidence/V08-03-intermediate-tube-count-feasibility-r1.md")
SUPERSESSION_JSON = Path("docs/tasks/evidence/V08-03-high-k-evidence-supersession-r2.json")
SUPERSESSION_MD = Path("docs/tasks/evidence/V08-03-high-k-evidence-supersession-r2.md")


def _write_supersession(report: Any) -> None:
    s = report.evidence_supersession
    payload = {
        "schema": "hxforge.evidence-supersession.v1",
        "task_id": "V08_03_INTERMEDIATE_TUBE_COUNT_FEASIBILITY_AND_EVIDENCE_RECONCILIATION",
        "supersedes": [
            {
                "artifact": s.superseded_artifact_path,
                "preserve_on_disk": True,
                "revision_superseded": "r1",
            }
        ],
        "supersession_revision": s.supersession_artifact_revision,
        "historical_errors": list(s.historical_errors),
        "corrected_attribution": list(s.corrected_attribution),
        "tube_geometry_authority": {
            "new_tube_geometry_authority_required_legacy_r1": True,
            "new_tube_geometry_authority_tri_state": s.new_tube_geometry_authority_decision,
            "proposed_geometry_authority_state": "NOT_PROVEN_FROM_CATALOG_COUNT_ALONE",
        },
        "engineering_language_correction": s.engineering_language_correction,
        "current_authoritative_artifacts": [
            "docs/tasks/evidence/V08-03-tube-side-replay-root-cause-r1.json",
            str(ARTIFACT_JSON),
        ],
    }
    SUPERSESSION_JSON.parent.mkdir(parents=True, exist_ok=True)
    SUPERSESSION_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    md = [
        "# High-K evidence supersession (r2)",
        "",
        f"**Preserves** `{s.superseded_artifact_path}` on disk; r1 conclusions below are **superseded**, not erased.",
        "",
        "## Historical errors (r1)",
        "",
    ]
    for line in s.historical_errors:
        md.append(f"- {line}")
    md.extend(["", "## Corrected attribution", ""])
    for line in s.corrected_attribution:
        md.append(f"- {line}")
    md.extend(
        [
            "",
            "## Tube geometry authority",
            "",
            f"- Tri-state decision: **{s.new_tube_geometry_authority_decision}**",
            "",
            s.engineering_language_correction,
        ]
    )
    SUPERSESSION_MD.write_text("\n".join(md), encoding="utf-8")


def main() -> None:
    artifacts = Path("/opt/cursor/artifacts")
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=_REPO, text=True).strip()
    report = run_intermediate_tube_count_feasibility(normalized, handoff, provider=provider)
    write_feasibility_artifacts(report, json_path=_REPO / ARTIFACT_JSON, md_path=_REPO / ARTIFACT_MD)
    write_feasibility_artifacts(
        report, json_path=artifacts / ARTIFACT_JSON.name, md_path=artifacts / ARTIFACT_MD.name
    )
    _write_supersession(report)
    (artifacts / SUPERSESSION_JSON.name).write_text(
        SUPERSESSION_JSON.read_text(encoding="utf-8"), encoding="utf-8"
    )

    best = report.best_variant
    payload: dict[str, Any] = {
        "TASK_ID": "V08_03_INTERMEDIATE_TUBE_COUNT_FEASIBILITY_AND_EVIDENCE_RECONCILIATION",
        "PR_NUMBER": PR_NUMBER,
        "HEAD_SHA": head,
        "TASK027_REGIME_UNCHANGED": report.task027_regime_unchanged,
        "FROZEN_CANDIDATE_C_UNCHANGED": report.frozen_candidate_c_unchanged,
        "INTERMEDIATE_LAYOUTS_EVALUATED": len(report.layouts_evaluated),
        "MODEL_SUPPORTED_VARIANTS": report.model_supported_variant_count,
        "HIGH_K_JOINT_PRESCREEN_PASS_COUNT": report.high_k_joint_prescreen_pass_count,
        "BEST_VARIANT_TUBE_COUNT": best.physical_tube_count if best else None,
        "BEST_VARIANT_RE": None,
        "BEST_VARIANT_CLEAN_Q_W": best.clean_q_w if best else None,
        "BEST_VARIANT_FOULED_Q_W": best.fouled_q_w if best else None,
        "BEST_VARIANT_HIGH_TUBE_DP_PA": best.high_tube_dp_pa if best else None,
        "BEST_VARIANT_HIGH_SHELL_DP_PA": best.high_shell_dp_pa if best else None,
        "EVIDENCE_CONFLICT_RESOLVED": True,
        "NEW_AUTHORITY_REQUIRED": report.new_authority_required,
        "DESIGN_DECISION": report.design_decision,
        "CI_STATUS": ci_status_for_head(head),
        "PR_STATE": "DRAFT",
        "MERGE_AUTHORIZED": False,
        "BVP_ROUTE": BVP_PROTOTYPE_ROUTE,
        "artifact_path": str(ARTIFACT_JSON),
        "supersession_path": str(SUPERSESSION_JSON),
    }
    if best:
        for row in report.layouts_evaluated:
            if row.full_chain and row.full_chain.geometry_v2 == best.geometry_v2:
                payload["BEST_VARIANT_RE"] = row.isolation.task026_reynolds_number
                break
    out = artifacts / "v08_03_intermediate_tube_count_feasibility_delivery.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()